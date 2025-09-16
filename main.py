from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.storage.jsonstore import JsonStore
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.utils import platform
from kivy.config import Config
import random

# Настройки окна для разных платформ
Config.set('graphics', 'resizable', '1')
if platform in ('win', 'linux', 'macosx', 'unknown'):
    Window.size = (400, 600)
else:
    Window.fullscreen = 'auto'


# Кастомное текстовое поле с автоматическим изменением высоты
class AutoHeightTextInput(TextInput):
    min_height = NumericProperty(dp(40))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(text=self.on_text_change)
        self.height = self.min_height

    def on_text_change(self, instance, value):
        # Вычисляем необходимую высоту на основе текста
        text_width = self.width - self.padding[0] - self.padding[2]
        lines = len(self._lines)
        line_height = self.line_height + self.line_spacing
        new_height = max(self.min_height, lines * line_height + self.padding[1] + self.padding[3])

        if new_height != self.height:
            self.height = new_height
            # Обновляем layout родительского контейнера
            if self.parent:
                self.parent.height = new_height
                if hasattr(self.parent.parent, 'height'):
                    self.parent.parent.height = new_height


class AddQuestionTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        self.option_widgets = []  # Храним виджеты вариантов ответов

        # Поле вопроса
        question_layout = BoxLayout(size_hint_y=None, height=dp(60))
        question_layout.add_widget(Label(text='Вопрос:', size_hint_x=0.3, font_size=dp(16)))
        self.question_input = AutoHeightTextInput(
            multiline=True,
            size_hint_x=0.7,
            min_height=dp(40),
            font_size=dp(14)
        )
        question_layout.add_widget(self.question_input)
        self.add_widget(question_layout)

        # Область для вариантов ответов
        options_label = Label(
            text='Варианты ответов (отметьте правильные):',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16)
        )
        self.add_widget(options_label)

        self.options_scroll = ScrollView(size_hint=(1, 0.6))
        self.options_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.options_scroll.add_widget(self.options_layout)
        self.add_widget(self.options_scroll)

        # Кнопки управления вариантами
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.add_btn = Button(text='Добавить вариант', font_size=dp(14))
        self.add_btn.bind(on_press=self.add_option)
        btn_layout.add_widget(self.add_btn)

        self.remove_btn = Button(text='Удалить вариант', font_size=dp(14))
        self.remove_btn.bind(on_press=self.remove_option)
        btn_layout.add_widget(self.remove_btn)
        self.add_widget(btn_layout)

        # Кнопка сохранения вопроса
        self.save_btn = Button(text='Добавить вопрос', size_hint_y=None, height=dp(50), font_size=dp(16))
        self.save_btn.bind(on_press=self.save_question)
        self.add_widget(self.save_btn)

        # Добавляем начальные два варианта
        self.add_option()
        self.add_option()

    def add_option(self, instance=None):
        if len(self.option_widgets) >= 6:
            self.show_popup("Информация", "Максимальное количество вариантов - 6")
            return

        option_layout = BoxLayout(size_hint_y=None, height=dp(60))

        # Чекбокс для правильного ответа
        checkbox = CheckBox(size_hint_x=0.2)

        # Поле для текста варианта
        text_input = AutoHeightTextInput(
            multiline=True,
            size_hint_x=0.8,
            min_height=dp(40),
            font_size=dp(14),
            hint_text=f"Вариант {len(self.option_widgets) + 1}"
        )

        option_layout.add_widget(checkbox)
        option_layout.add_widget(text_input)
        self.options_layout.add_widget(option_layout)
        self.option_widgets.append((checkbox, text_input))

    def remove_option(self, instance):
        if len(self.option_widgets) > 2:
            last_option = self.option_widgets.pop()
            self.options_layout.remove_widget(last_option[0].parent)
        else:
            self.show_popup("Информация", "Минимальное количество вариантов - 2")

    def save_question(self, instance):
        question_text = self.question_input.text.strip()
        options = []
        correct_options = []

        # Собираем данные из полей
        for i, (checkbox, text_input) in enumerate(self.option_widgets):
            option_text = text_input.text.strip()
            if option_text:  # Игнорируем пустые варианты
                options.append(option_text)
                if checkbox.active:
                    correct_options.append(str(i + 1))

        # Проверяем валидность данных
        if not question_text:
            self.show_popup("Ошибка", "Введите вопрос!")
            return

        if len(options) < 2:
            self.show_popup("Ошибка", "Должно быть хотя бы два варианта ответа!")
            return

        if not correct_options:
            self.show_popup("Ошибка", "Выберите хотя бы один правильный ответ!")
            return

        # Сохраняем вопрос
        store = JsonStore('questions.json')
        questions = store.get('questions')['data'] if store.exists('questions') else []

        question_data = {
            'question': question_text,
            'options': options,
            'correct': correct_options
        }

        questions.append(question_data)
        store.put('questions', data=questions)

        # Очищаем форму
        self.question_input.text = ''
        for checkbox, text_input in self.option_widgets:
            checkbox.active = False
            text_input.text = ''

        # Оставляем только два варианта
        while len(self.option_widgets) > 2:
            self.remove_option(None)

        self.show_popup("Успех", "Вопрос добавлен!")

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10))
        popup_layout.add_widget(Label(text=message, font_size=dp(16)))
        close_btn = Button(text='OK', size_hint_y=None, height=dp(40), font_size=dp(16))
        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup_layout.add_widget(close_btn)
        popup.open()


class ExamTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        self.current_question = None
        self.correct_indices = []
        self.checkboxes = []

        # Поле вопроса
        self.question_label = Label(
            text='Загрузка вопросов...',
            size_hint_y=None,
            height=dp(150),
            text_size=(Window.width - dp(20), None),
            halign='left',
            valign='top',
            font_size=dp(20),
            bold=True
        )
        self.question_label.bind(size=self.question_label.setter('text_size'))
        self.add_widget(self.question_label)

        # Область для вариантов ответов
        options_label = Label(
            text='Выберите все правильные ответы:',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16)
        )
        self.add_widget(options_label)

        self.options_scroll = ScrollView(size_hint=(1, 0.6))
        self.options_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.options_scroll.add_widget(self.options_layout)
        self.add_widget(self.options_scroll)

        # Кнопка проверки
        self.check_btn = Button(
            text='Проверить',
            size_hint_y=None,
            height=dp(50),
            font_size=dp(16)
        )
        self.check_btn.bind(on_press=self.check_answer)
        self.add_widget(self.check_btn)

        self.load_question()

    def clear_options(self):
        self.options_layout.clear_widgets()
        self.checkboxes = []

    def load_question(self):
        self.clear_options()

        store = JsonStore('questions.json')
        if not store.exists('questions'):
            self.question_label.text = "В базе нет вопросов! Добавьте вопросы на вкладке 'Добавить вопрос'."
            self.check_btn.disabled = True
            return

        questions = store.get('questions')['data']
        if not questions:
            self.question_label.text = "В базе нет вопросов! Добавьте вопросы на вкладке 'Добавить вопрос'."
            self.check_btn.disabled = True
            return

        self.check_btn.disabled = False
        self.current_question = random.choice(questions)

        # Устанавливаем текст вопроса
        self.question_label.text = self.current_question['question']

        # Получаем правильные ответы
        self.correct_indices = [int(idx) - 1 for idx in self.current_question['correct']]

        # Создаем чекбоксы для вариантов ответов
        for i, option in enumerate(self.current_question['options']):
            option_layout = BoxLayout(size_hint_y=None, height=dp(80))
            checkbox = CheckBox(size_hint_x=0.2)
            label = Label(
                text=option,
                text_size=(Window.width - dp(60), None),
                halign='left',
                valign='middle',
                font_size=dp(16)
            )
            label.bind(size=label.setter('text_size'))
            option_layout.add_widget(checkbox)
            option_layout.add_widget(label)
            self.options_layout.add_widget(option_layout)
            self.checkboxes.append(checkbox)

    def check_answer(self, instance):
        selected_indices = []
        for i, checkbox in enumerate(self.checkboxes):
            if checkbox.active:
                selected_indices.append(i)

        if not selected_indices:
            self.show_popup("Ошибка", "Выберите хотя бы один ответ!")
            return

        if set(selected_indices) == set(self.correct_indices):
            self.show_popup("Правильно!", "Все ответы верные!", self.load_question)
        else:
            # Формируем список правильных ответов
            correct_answers = []
            for i in self.correct_indices:
                correct_answers.append(self.current_question['options'][i])

            correct_text = "\n".join(f"- {answer}" for answer in correct_answers)
            self.show_popup("Неправильно!", f"Правильные ответы:\n{correct_text}", self.load_question)

    def show_popup(self, title, message, callback=None):
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        popup_layout.add_widget(Label(text=message, font_size=dp(16)))
        close_btn = Button(text='OK', size_hint_y=None, height=dp(40), font_size=dp(16))
        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.5))

        def dismiss_and_callback(instance):
            popup.dismiss()
            if callback:
                callback()

        close_btn.bind(on_press=dismiss_and_callback)
        popup_layout.add_widget(close_btn)
        popup.open()


class ExamApp(App):
    def build(self):
        # Создаем панель с вкладками
        tabs = TabbedPanel(do_default_tab=False)

        # Вкладка добавления вопросов
        add_tab = TabbedPanelItem(text='Добавить\nвопрос')
        add_content = AddQuestionTab()
        add_tab.add_widget(add_content)
        tabs.add_widget(add_tab)

        # Вкладка экзамена
        exam_tab = TabbedPanelItem(text='Экзамен')
        exam_content = ExamTab()
        exam_tab.add_widget(exam_content)
        tabs.add_widget(exam_tab)

        return tabs


if __name__ == '__main__':
    ExamApp().run()
