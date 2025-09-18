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
from kivy.metrics import dp
from kivy.properties import NumericProperty, ObjectProperty
from kivy.utils import platform
from kivy.config import Config
from kivy.graphics import Color, Rectangle
import random
import os
import json
from kivy.logger import Logger
import time

# Настройки окна для разных платформ
Config.set('graphics', 'resizable', '1')
if platform in ('win', 'linux', 'macosx', 'unknown'):
    Window.size = (400, 600)
else:
    Window.fullscreen = 'auto'

if platform == 'android':
    try:
        from android import mActivity
        from android.storage import app_storage_path
        from android.permissions import request_permissions, Permission
        from jnius import autoclass

        # Запрашиваем разрешения
        request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                             Permission.READ_EXTERNAL_STORAGE,
                             Permission.MANAGE_EXTERNAL_STORAGE])

        # Используем внутреннее хранилище приложения
        storage_path = app_storage_path()
        data_dir = os.path.join(storage_path, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        QUESTIONS_FILE = os.path.join(data_dir, 'questions.json')
    except Exception as e:
        Logger.error(f"Android init error: {e}")
        QUESTIONS_FILE = 'questions.json'
else:
    QUESTIONS_FILE = 'questions.json'


def load_questions():
    """Загружает вопросы из файла с проверкой формата"""
    try:
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                questions = json.load(f)

            # Проверяем, что questions является списком
            if not isinstance(questions, list):
                Logger.error(f"Invalid questions format: {type(questions)}")
                return []

            # Фильтруем только валидные вопросы
            valid_questions = []
            for item in questions:
                if (isinstance(item, dict) and
                        'question' in item and
                        'options' in item and
                        'correct' in item):
                    valid_questions.append(item)
                else:
                    Logger.warning(f"Invalid question format: {item}")

            return valid_questions
        else:
            return []
    except Exception as e:
        Logger.error(f"Error loading questions: {e}")
        return []


def save_questions(questions):
    """Сохраняет вопросы в файл"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Создаем директорию, если она не существует
            dir_name = os.path.dirname(QUESTIONS_FILE)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)

            with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            Logger.error(f"Error saving questions (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Небольшая задержка перед повторной попыткой
            else:
                return False


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


# Кастомный Label с возможностью изменения цвета фона
class AutoHeightLabel(Label):
    min_height = NumericProperty(dp(40))

    def __init__(self, **kwargs):
        # Извлекаем padding_x и padding_y из kwargs, если они есть
        self.padding_x = kwargs.pop('padding_x', 0)
        self.padding_y = kwargs.pop('padding_y', 0)
        super().__init__(**kwargs)
        self.bind(text=self.on_text_change)
        self.height = self.min_height

    def on_text_change(self, instance, value):
        # Вычисляем необходимую высоту на основе текста с учетом отступов
        text_width = self.width - self.padding_x * 2
        if text_width <= 0:
            return

        # Создаем временный текстур для расчета высоты
        from kivy.core.text import Label as CoreLabel
        core_label = CoreLabel(
            text=self.text,
            font_size=self.font_size,
            font_name=self.font_name,
            text_size=(text_width, None)
        )
        core_label.refresh()

        # Вычисляем высоту с учетом отступов
        new_height = max(self.min_height, core_label.texture.height + self.padding_y * 2)

        if new_height != self.height:
            self.height = new_height


class ExamApp(App):
    questions_updated = ObjectProperty(None)

    def build(self):
        # Создаем панель с вкладками
        self.tabs = TabbedPanel(do_default_tab=False)

        # Вкладка добавления вопросов
        add_tab = TabbedPanelItem(text='Добавить\nвопрос')
        self.add_content = AddQuestionTab(app=self)
        add_tab.add_widget(self.add_content)
        self.tabs.add_widget(add_tab)

        # Вкладка редактирования вопросов
        edit_tab = TabbedPanelItem(text='Редактировать\nвопросы')
        self.edit_content = EditQuestionsTab(app=self)
        edit_tab.add_widget(self.edit_content)
        self.tabs.add_widget(edit_tab)

        # Вкладка экзамена
        exam_tab = TabbedPanelItem(text='Экзамен')
        self.exam_content = ExamTab(app=self)
        exam_tab.add_widget(self.exam_content)
        self.tabs.add_widget(exam_tab)

        return self.tabs

    def update_questions(self):
        # Этот метод будет вызываться при изменении вопросов
        if hasattr(self, 'exam_content'):
            self.exam_content.reset_session()
        if hasattr(self, 'edit_content'):
            self.edit_content.load_questions()


class AddQuestionTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
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

        # Загружаем существующие вопросы
        questions = load_questions()

        # Добавляем новый вопрос
        question_data = {
            'question': question_text,
            'options': options,
            'correct': correct_options
        }

        questions.append(question_data)

        # Сохраняем вопросы
        if not save_questions(questions):
            self.show_popup("Ошибка", "Не удалось сохранить вопрос! Проверьте разрешения приложения.")
            return

        # Очищаем форму
        self.question_input.text = ''
        for checkbox, text_input in self.option_widgets:
            checkbox.active = False
            text_input.text = ''

        # Оставляем только два варианта
        while len(self.option_widgets) > 2:
            self.remove_option(None)

        # Уведомляем приложение об обновлении вопросов
        self.app.update_questions()

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
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        self.current_question = None
        self.correct_indices = []
        self.checkboxes = []
        self.option_labels = []
        self.used_questions = set()
        self.answered = False
        self.answer_correct = False

        # Поле вопроса с ScrollView для длинных вопросов
        question_scroll = ScrollView(size_hint_y=None, height=dp(150))
        self.question_label = AutoHeightLabel(
            text='Загрузка вопросов...',
            size_hint_y=None,
            text_size=(Window.width - dp(30), None),  # Учитываем padding скролла
            halign='left',
            valign='top',
            font_size=dp(18),  # Немного уменьшили шрифт для лучшего отображения
            bold=True,
            color=(1, 1, 0, 1),
            min_height=dp(150),
            padding_x=dp(10),  # Добавили отступы
            padding_y=dp(10)
        )
        self.question_label.bind(size=self.question_label.setter('text_size'))
        question_scroll.add_widget(self.question_label)
        self.add_widget(question_scroll)

        # Область для вариантов ответов
        options_label = Label(
            text='Выберите все правильные ответы:',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16),
            color=(0, 0, 0, 1)
        )
        self.add_widget(options_label)

        self.options_scroll = ScrollView(size_hint=(1, 0.6))
        self.options_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.options_scroll.add_widget(self.options_layout)
        self.add_widget(self.options_scroll)

        # Кнопка ответа/продолжения
        self.answer_btn = Button(
            text='Ответить',
            size_hint_y=None,
            height=dp(50),
            font_size=dp(16)
        )
        self.answer_btn.bind(on_press=self.on_answer_btn_press)
        self.add_widget(self.answer_btn)

        # Статус ответа
        self.status_label = Label(
            text='',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(16),
            bold=True,
            color=(0, 0, 0, 1)
        )
        self.add_widget(self.status_label)

        self.load_question()

    def reset_session(self):
        """Сбросить сессию и начать заново"""
        self.used_questions.clear()
        self.load_question()

    def clear_options(self):
        self.options_layout.clear_widgets()
        self.checkboxes = []
        self.option_labels = []

    def load_question(self):
        self.clear_options()
        self.answered = False
        self.answer_btn.text = 'Ответить'
        self.status_label.text = ''

        # Загружаем вопросы
        questions = load_questions()

        if not questions:
            self.question_label.text = "В базе нет вопросов! Добавьте вопросы на вкладке 'Добавить вопрос'."
            self.answer_btn.disabled = True
            return

        # Проверяем, остались ли неиспользованные вопросы
        available_questions = [q for q in questions if q['question'] not in self.used_questions]

        if not available_questions:
            self.question_label.text = "Все вопросы закончились! Обновите сессию на вкладке редактирования."
            self.answer_btn.disabled = True
            return

        self.answer_btn.disabled = False

        # Выбираем случайный вопрос из доступных и перемешиваем варианты ответов
        self.current_question = random.choice(available_questions)
        self.used_questions.add(self.current_question['question'])

        # Создаем перемешанный список вариантов ответов
        options_with_indices = list(enumerate(self.current_question['options']))
        random.shuffle(options_with_indices)

        # Сохраняем правильные ответы в соответствии с новым порядком
        original_correct = [int(idx) - 1 for idx in self.current_question['correct']]
        self.correct_indices = []

        for new_index, (original_index, option_text) in enumerate(options_with_indices):
            if original_index in original_correct:
                self.correct_indices.append(new_index)

        # Устанавливаем текст вопроса
        if self.current_question:
            self.question_label.text = self.current_question['question']
        else:
            self.question_label.text = "Ошибка загрузки вопроса"
            return

        # Создаем чекбоксы для вариантов ответов (в перемешанном порядке)
        for new_index, (original_index, option_text) in enumerate(options_with_indices):
            option_layout = BoxLayout(size_hint_y=None, height=dp(100), spacing=dp(10))  # Добавили spacing

            checkbox = CheckBox(size_hint_x=0.2)
            checkbox.disabled = self.answered  # Блокируем чекбоксы после ответа

            # Используем AutoHeightLabel для автоматического изменения высоты
            label = AutoHeightLabel(
                text=option_text,
                text_size=(Window.width - dp(80), None),  # Уменьшили ширину для учета padding
                halign='left',
                valign='middle',
                font_size=dp(16),
                color=(0, 0, 0, 1),  # Черный цвет текста
                min_height=dp(80),  # Минимальная высота для длинных ответов
                padding_x=dp(10)  # Добавили горизонтальные отступы
            )

            # Добавляем белый фон только для текста ответа
            with label.canvas.before:
                Color(1, 1, 1, 1)  # Белый цвет
                label.rect = Rectangle(pos=label.pos, size=label.size)

            # Обновляем прямоугольник при изменении размера или позиции
            label.bind(pos=self.update_label_rect, size=self.update_label_rect)
            label.bind(size=label.setter('text_size'))

            option_layout.add_widget(checkbox)
            option_layout.add_widget(label)
            self.options_layout.add_widget(option_layout)
            self.checkboxes.append(checkbox)
            self.option_labels.append(label)

        # Добавьте новый метод для обновления прямоугольника фона текста
    def update_label_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

    def on_answer_btn_press(self, instance):
        if not self.answered:
            self.check_answer()
        else:
            self.load_question()

    # В методе check_answer измените подсветку фона:
    def check_answer(self):
        selected_indices = []
        for i, checkbox in enumerate(self.checkboxes):
            if checkbox.active:
                selected_indices.append(i)

        if not selected_indices:
            self.status_label.text = "Выберите хотя бы один ответ!"
            self.status_label.color = (1, 0, 0, 1)  # Красный цвет
            return

        # Блокируем чекбоксы после ответа
        for checkbox in self.checkboxes:
            checkbox.disabled = True

        self.answered = True
        self.answer_btn.text = 'Далее'

        # Проверяем правильность ответа
        if set(selected_indices) == set(self.correct_indices):
            self.status_label.text = "Правильно!"
            self.status_label.color = (0, 1, 0, 1)  # Зеленый цвет
            self.answer_correct = True

            # Подсвечиваем правильные ответы зеленым (только текст)
            for i in self.correct_indices:
                self.option_labels[i].canvas.before.clear()
                with self.option_labels[i].canvas.before:
                    Color(0.7, 1, 0.7, 1)  # Светло-зеленый
                    Rectangle(pos=self.option_labels[i].pos, size=self.option_labels[i].size)
        else:
            self.status_label.text = "Неправильно!"
            self.status_label.color = (1, 0, 0, 1)  # Красный цвет
            self.answer_correct = False

            # Подсвечиваем выбранные неправильные ответы красным (только текст)
            for i in selected_indices:
                if i not in self.correct_indices:
                    self.option_labels[i].canvas.before.clear()
                    with self.option_labels[i].canvas.before:
                        Color(1, 0.7, 0.7, 1)  # Светло-красный
                        Rectangle(pos=self.option_labels[i].pos, size=self.option_labels[i].size)

            # Подсвечиваем правильные ответы зеленым (только текст)
            for i in self.correct_indices:
                self.option_labels[i].canvas.before.clear()
                with self.option_labels[i].canvas.before:
                    Color(0.7, 1, 0.7, 1)  # Светло-зеленый
                    Rectangle(pos=self.option_labels[i].pos, size=self.option_labels[i].size)

    def clear_options(self):
        # Очищаем все виджеты и списки
        self.options_layout.clear_widgets()
        self.checkboxes = []
        self.option_labels = []


class EditQuestionsTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        self.current_edit_index = None

        # Заголовок
        title_label = Label(
            text='Редактирование вопросов',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(20),
            bold=True
        )
        self.add_widget(title_label)

        # Прокручиваемый список вопросов
        self.questions_scroll = ScrollView(size_hint=(1, 0.6))  # Уменьшили высоту списка
        self.questions_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.questions_layout.bind(minimum_height=self.questions_layout.setter('height'))
        self.questions_scroll.add_widget(self.questions_layout)
        self.add_widget(self.questions_scroll)

        # Кнопка обновления списка
        self.refresh_btn = Button(
            text='Обновить список',
            size_hint_y=None,
            height=dp(40),  # Уменьшили высоту кнопки
            font_size=dp(14)
        )
        self.refresh_btn.bind(on_press=self.load_questions)
        self.add_widget(self.refresh_btn)

        # Кнопки экспорта и импорта
        export_import_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))  # Уменьшили высоту и отступы

        self.export_btn = Button(
            text='Экспорт',
            size_hint_x=0.5,  # Уже кнопки
            font_size=dp(12)  # Меньший шрифт
        )
        self.export_btn.bind(on_press=self.export_database)
        export_import_layout.add_widget(self.export_btn)

        self.import_btn = Button(
            text='Импорт',
            size_hint_x=0.5,  # Уже кнопки
            font_size=dp(12)  # Меньший шрифт
        )
        self.import_btn.bind(on_press=self.import_database)
        export_import_layout.add_widget(self.import_btn)

        self.add_widget(export_import_layout)

        # Кнопка сброса сессии экзамена
        self.reset_session_btn = Button(
            text='Сбросить сессию',
            size_hint_y=None,
            height=dp(40),  # Уменьшили высоту кнопки
            font_size=dp(12)  # Меньший шрифт
        )
        self.reset_session_btn.bind(on_press=self.reset_exam_session)
        self.add_widget(self.reset_session_btn)

        self.load_questions()

    def reset_exam_session(self, instance):
        """Сбросить сессию экзамена"""
        if hasattr(self.app, 'exam_content'):
            self.app.exam_content.reset_session()
            self.show_popup("Успех", "Сессия экзамена сброшена!")

    def load_questions(self, instance=None):
        self.questions_layout.clear_widgets()

        # Загружаем вопросы
        questions = load_questions()

        if not questions:
            no_questions_label = Label(
                text='В базе нет вопросов.',
                size_hint_y=None,
                height=dp(40),
                font_size=dp(16)
            )
            self.questions_layout.add_widget(no_questions_label)
            return

        for idx, question in enumerate(questions):
            question_item = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))  # Уменьшили высоту и отступы

            # Текст вопроса (обрезаем если слишком длинный)
            question_text = question['question']
            if len(question_text) > 40:  # Уменьшили длину обрезаемого текста
                question_text = question_text[:37] + '...'

            question_label = Label(
                text=question_text,
                size_hint_x=0.7,  # Увеличили ширину для текста
                text_size=(Window.width * 0.7 - dp(20), None),
                halign='left',
                valign='middle'
            )
            question_label.bind(size=question_label.setter('text_size'))

            # Кнопки редактирования и удаления
            btn_layout = BoxLayout(size_hint_x=0.3, spacing=dp(2))  # Уменьшили отступы

            edit_btn = Button(text='Ред.', size_hint_x=0.5, font_size=dp(12))  # Меньший шрифт
            edit_btn.bind(on_press=lambda instance, current_idx=idx: self.edit_question(current_idx, questions))

            delete_btn = Button(text='Удл.', size_hint_x=0.5, font_size=dp(12))  # Меньший шрифт
            delete_btn.bind(on_press=lambda instance, current_idx=idx: self.delete_question(current_idx, questions))

            btn_layout.add_widget(edit_btn)
            btn_layout.add_widget(delete_btn)

            question_item.add_widget(question_label)
            question_item.add_widget(btn_layout)

            self.questions_layout.add_widget(question_item)

    def edit_question(self, index, questions):
        self.current_edit_index = index
        question_data = questions[index]

        # Создаем попап для редактирования
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        popup = Popup(title='Редактирование вопроса', content=popup_layout,
                      size_hint=(0.95, 0.9))  # Увеличили ширину попапа

        # Поле вопроса
        question_input = AutoHeightTextInput(
            text=question_data['question'],
            multiline=True,
            size_hint_y=None,
            min_height=dp(40),
            font_size=dp(14)
        )
        popup_layout.add_widget(Label(text='Вопрос:', size_hint_y=None, height=dp(30)))
        popup_layout.add_widget(question_input)

        # Область для вариантов ответов
        options_label = Label(
            text='Варианты ответов (отметьте правильные):',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16)
        )
        popup_layout.add_widget(options_label)

        options_scroll = ScrollView(size_hint=(1, 0.5))
        options_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        options_layout.bind(minimum_height=options_layout.setter('height'))
        options_scroll.add_widget(options_layout)
        popup_layout.add_widget(options_scroll)

        option_widgets = []

        # Добавляем существующие варианты ответов
        for i, option in enumerate(question_data['options']):
            option_layout = BoxLayout(size_hint_y=None, height=dp(60))

            checkbox = CheckBox(size_hint_x=0.2)
            # Отмечаем правильные ответы
            if str(i + 1) in question_data['correct']:
                checkbox.active = True

            text_input = AutoHeightTextInput(
                text=option,
                multiline=True,
                size_hint_x=0.8,
                min_height=dp(40),
                font_size=dp(14)
            )

            option_layout.add_widget(checkbox)
            option_layout.add_widget(text_input)
            options_layout.add_widget(option_layout)
            option_widgets.append((checkbox, text_input))

        # Кнопки управления вариантами
        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))  # Уменьшили высоту и отступы
        add_btn = Button(text='Добавить', font_size=dp(12))  # Меньший шрифт
        remove_btn = Button(text='Удалить', font_size=dp(12))  # Меньший шрифт
        btn_layout.add_widget(add_btn)
        btn_layout.add_widget(remove_btn)
        popup_layout.add_widget(btn_layout)

        # Кнопки сохранения и отмены
        btn_layout2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))  # Уменьшили высоту и отступы
        save_btn = Button(text='Сохранить', font_size=dp(14))
        cancel_btn = Button(text='Отмена', font_size=dp(14))
        btn_layout2.add_widget(save_btn)
        btn_layout2.add_widget(cancel_btn)
        popup_layout.add_widget(btn_layout2)

        # Функции для кнопок
        def add_option(instance):
            if len(option_widgets) >= 6:
                self.show_popup("Информация", "Максимальное количество вариантов - 6")
                return

            option_layout = BoxLayout(size_hint_y=None, height=dp(60))
            checkbox = CheckBox(size_hint_x=0.2)
            text_input = AutoHeightTextInput(
                multiline=True,
                size_hint_x=0.8,
                min_height=dp(40),
                font_size=dp(14),
                hint_text="Новый вариант"
            )

            option_layout.add_widget(checkbox)
            option_layout.add_widget(text_input)
            options_layout.add_widget(option_layout)
            option_widgets.append((checkbox, text_input))

        def remove_option(instance):
            if len(option_widgets) > 2:
                last_option = option_widgets.pop()
                options_layout.remove_widget(last_option[0].parent)
            else:
                self.show_popup("Информация", "Минимальное количество вариантов - 2")

        def save_question(instance):
            nonlocal option_widgets
            new_question_text = question_input.text.strip()
            options = []
            correct_options = []

            # Собираем данные из полей
            for i, (checkbox, text_input) in enumerate(option_widgets):
                option_text = text_input.text.strip()
                if option_text:  # Игнорируем пустые варианты
                    options.append(option_text)
                    if checkbox.active:
                        correct_options.append(str(i + 1))

            # Проверяем валидность данных
            if not new_question_text:
                self.show_popup("Ошибка", "Введите вопрос!")
                return

            if len(options) < 2:
                self.show_popup("Ошибка", "Должно быть хотя бы два варианта ответа!")
                return

            if not correct_options:
                self.show_popup("Ошибка", "Выберите хотя бы один правильный ответ!")
                return

            # Обновляем вопрос
            questions[self.current_edit_index] = {
                'question': new_question_text,
                'options': options,
                'correct': correct_options
            }

            # Сохраняем вопросы
            if not save_questions(questions):
                self.show_popup("Ошибка", "Не удалось сохранить вопросы!")
                return

            popup.dismiss()
            self.load_questions()
            # Уведомляем приложение об обновлении вопросов
            self.app.update_questions()
            self.show_popup("Успех", "Вопрос обновлен!")

        def cancel_edit(instance):
            popup.dismiss()

        add_btn.bind(on_press=add_option)
        remove_btn.bind(on_press=remove_option)
        save_btn.bind(on_press=save_question)
        cancel_btn.bind(on_press=cancel_edit)

        popup.open()

    def delete_question(self, index, questions):
        if 0 <= index < len(questions):
            # Подтверждение удаления
            confirm_layout = BoxLayout(orientation='vertical', padding=dp(10))
            confirm_label = Label(
                text=f'Вы уверены, что хотите удалить вопрос?\n\n{questions[index]["question"][:50]}...',
                text_size=(Window.width * 0.8 - dp(20), None)
            )
            confirm_layout.add_widget(confirm_label)

            btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            yes_btn = Button(text='Да', font_size=dp(16))
            no_btn = Button(text='Нет', font_size=dp(16))
            btn_layout.add_widget(yes_btn)
            btn_layout.add_widget(no_btn)
            confirm_layout.add_widget(btn_layout)

            confirm_popup = Popup(title='Подтверждение удаления', content=confirm_layout,
                                  size_hint=(0.8, 0.4))

            def confirm_delete(instance):
                questions.pop(index)

                # Сохраняем вопросы
                if not save_questions(questions):
                    self.show_popup("Ошибка", "Не удалось сохранить вопросы!")
                    return

                confirm_popup.dismiss()
                self.load_questions()
                # Уведомляем приложение об обновлении вопросов
                self.app.update_questions()
                self.show_popup("Успех", "Вопрос удален!")

            def cancel_delete(instance):
                confirm_popup.dismiss()

            yes_btn.bind(on_press=confirm_delete)
            no_btn.bind(on_press=cancel_delete)

            confirm_popup.open()

    def export_database(self, instance):
        try:
            # Загружаем текущие вопросы
            questions = load_questions()

            if platform == 'android':
                # Получаем корневую директорию приложения на Android
                from jnius import autoclass
                from android import mActivity

                Context = autoclass('android.content.Context')
                context = mActivity.getApplicationContext()

                # Получаем путь к внутреннему хранилищу приложения
                files_dir = context.getFilesDir()
                internal_storage_path = files_dir.getAbsolutePath()

                # Сохраняем вопросы в корневую директорию приложения
                export_path = os.path.join(internal_storage_path, 'questions_export.json')

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, ensure_ascii=False, indent=2)

                # Более краткое сообщение
                self.show_popup("Успех",
                                "База данных экспортирована во внутреннее хранилище приложения.\n\nФайл: questions_export.json")
            else:
                # На других платформах используем домашнюю директорию
                home_dir = os.path.expanduser("~")
                export_path = os.path.join(home_dir, 'questions_export.json')

                # Сохраняем вопросы в файл экспорта
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, ensure_ascii=False, indent=2)

                # Более краткое сообщение
                self.show_popup("Успех", f"База данных экспортирована:\n{os.path.basename(export_path)}")
        except Exception as e:
            # Сокращаем сообщение об ошибке
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            self.show_popup("Ошибка", f"Не удалось экспортировать базу:\n{error_msg}")

    def import_database(self, instance):
        try:
            if platform == 'android':
                # Получаем корневую директорию приложения на Android
                from jnius import autoclass
                from android import mActivity

                Context = autoclass('android.content.Context')
                context = mActivity.getApplicationContext()

                # Получаем путь к внутреннему хранилищу приложения
                files_dir = context.getFilesDir()
                internal_storage_path = files_dir.getAbsolutePath()

                # Ищем файл в корневой директории приложения
                import_path = os.path.join(internal_storage_path, 'questions_export.json')

                # Проверяем существование файла импорта
                if not os.path.exists(import_path):
                    self.show_popup("Ошибка",
                                    "Файл questions_export.json не найден во внутреннем хранилище приложения.")
                    return

                # Загружаем вопросы из файла импорта
                with open(import_path, 'r', encoding='utf-8') as f:
                    imported_questions = json.load(f)
            else:
                # На других платформах используем домашнюю директорию
                home_dir = os.path.expanduser("~")
                import_path = os.path.join(home_dir, 'questions_export.json')

                # Проверяем существование файла импорта
                if not os.path.exists(import_path):
                    self.show_popup("Ошибка", "Файл questions_export.json не найден в домашней директории.")
                    return

                # Загружаем вопросы из файла импорта
                with open(import_path, 'r', encoding='utf-8') as f:
                    imported_questions = json.load(f)

            # Проверяем валидность импортированных данных
            if not isinstance(imported_questions, list):
                self.show_popup("Ошибка", "Некорректный формат файла импорта")
                return

            # Сохраняем импортированные вопросы
            if save_questions(imported_questions):
                self.show_popup("Успех", "База данных успешно импортирована!")
                # Обновляем вопросы в приложении
                self.app.update_questions()
                self.load_questions()
            else:
                self.show_popup("Ошибка", "Не удалось сохранить импортированную базу данных")
        except Exception as e:
            # Сокращаем сообщение об ошибке
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            self.show_popup("Ошибка", f"Не удалось импортировать базу:\n{error_msg}")

    def show_popup(self, title, message):
        # Создаем ScrollView для длинных сообщений
        scroll = ScrollView(size_hint=(1, 0.8))

        # Уменьшаем размер шрифта для лучшего отображения
        label = Label(
            text=message,
            font_size=dp(14),  # Уменьшенный размер шрифта
            text_size=(Window.width * 0.7, None),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        label.bind(texture_size=label.setter('size'))

        scroll.add_widget(label)

        popup_layout = BoxLayout(orientation='vertical', padding=dp(10))
        popup_layout.add_widget(scroll)

        close_btn = Button(
            text='OK',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(16)
        )
        popup_layout.add_widget(close_btn)

        popup = Popup(
            title=title,
            content=popup_layout,
            size_hint=(0.9, 0.7)  # Увеличили размер попапа
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == '__main__':
    ExamApp().run()