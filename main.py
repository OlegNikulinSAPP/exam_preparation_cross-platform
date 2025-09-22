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
from kivy.properties import NumericProperty
from kivy.utils import platform
from kivy.config import Config
from kivy.graphics import Color, Rectangle
import random
import os
import json

# Настройки логирования
import logging

logging.basicConfig(level=logging.DEBUG)
Logger = logging.getLogger('ExamApp')

# Глобальная настройка для имени файла с вопросами
QUESTIONS_FILENAME = 'questions.json'
# Определение константы для заголовка всплывающего окна
POPUP_TITLE_INFO = "Информация"
# Определим константу для сообщений об ошибках
POPUP_TITLE_ERROR = "Ошибка"
# Константа для заголовков успешных действий
POPUP_TITLE_SUCCESS = "Успех"

# Настройки окна
Config.set('graphics', 'resizable', '1')
if platform in ('win', 'linux', 'macosx', 'unknown'):
    Window.size = (400, 600)
else:
    Window.fullscreen = 'auto'

# Определяем путь к файлу вопросов
if platform == 'android':
    try:
        from android.storage import app_storage_path  # type: ignore
        from android.permissions import request_permissions, Permission  # type: ignore

        # Запрашиваем разрешения
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        # Используем внутреннее хранилище приложения
        storage_path = app_storage_path()
        data_dir = os.path.join(storage_path, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        QUESTIONS_FILE = os.path.join(data_dir, QUESTIONS_FILENAME)
        Logger.info(f"Android data path: {QUESTIONS_FILE}")

    except Exception as e:
        Logger.error(f"Android init error: {e}")
        QUESTIONS_FILE = QUESTIONS_FILENAME
else:
    QUESTIONS_FILE = QUESTIONS_FILENAME


def load_questions():
    """Загружает вопросы из файла"""
    try:
        Logger.info(f"Loading questions from: {QUESTIONS_FILE}")
        if os.path.exists(QUESTIONS_FILE) and os.path.getsize(QUESTIONS_FILE) > 0:
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            Logger.info(f"Loaded {len(questions)} questions")
            return questions
        Logger.info("No questions file found or file is empty")
        return []
    except Exception as ex:
        Logger.error(f"Error loading questions: {str(ex)}")
        return []


def save_questions(questions):
    """Сохраняет вопросы в файл"""
    try:
        Logger.info(f"Saving {len(questions)} questions to: {QUESTIONS_FILE}")
        # Создаем директорию, если она не существует
        dir_name = os.path.dirname(QUESTIONS_FILE)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        # Проверяем, что файл был создан и содержит данные
        if os.path.exists(QUESTIONS_FILE) and os.path.getsize(QUESTIONS_FILE) > 0:
            Logger.info("Questions saved successfully")
            return True
        else:
            Logger.error("Failed to save questions")
            return False
    except Exception as ex:
        Logger.error(f"Error saving questions: {str(ex)}")
        return False


# Кастомное текстовое поле с автоматическим изменением высоты
class AutoHeightTextInput(TextInput):
    min_height = NumericProperty(dp(40))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(text=self.on_text_change)
        self.height = self.min_height

    def on_text_change(self, _instance, _value):
        """Автоматически изменяет высоту текстового поля при изменении текста"""
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


# Кастомный Label изменения цвета фона
class AutoHeightLabel(Label):
    min_height = NumericProperty(dp(40))

    def __init__(self, **kwargs):
        # Извлекаем padding_x и padding_y из kwargs, если они есть
        self.padding_x = kwargs.pop('padding_x', 0)
        self.padding_y = kwargs.pop('padding_y', 0)
        super().__init__(**kwargs)
        self.bind(text=self.on_text_change)
        self.height = self.min_height

    def on_text_change(self, _instance, _value):
        # Вычисляем необходимую высоту на основе текста с учетом отступов
        text_width = self.width - self.padding_x * 2
        if text_width <= 0:
            return

        # Создаем текстур для расчета высоты
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tabs = None
        self.add_content = None
        self.exam_content = None
        self.edit_content = None

    def build(self):
        # Создаем панель с вкладками
        self.tabs = TabbedPanel(do_default_tab=False)

        # Вкладка добавления вопросов
        add_tab = TabbedPanelItem(text='Добавить\nвопрос')
        self.add_content = AddQuestionTab(app=self)
        add_tab.add_widget(self.add_content)
        self.tabs.add_widget(add_tab)

        # Вкладка экзамена
        exam_tab = TabbedPanelItem(text='Экзамен')
        self.exam_content = ExamTab(app=self)
        exam_tab.add_widget(self.exam_content)
        self.tabs.add_widget(exam_tab)

        # Вкладка редактирования
        edit_tab = TabbedPanelItem(text='Редактировать')
        self.edit_content = EditQuestionsTab(app=self)
        edit_tab.add_widget(self.edit_content)
        self.tabs.add_widget(edit_tab)

        return self.tabs

    def update_questions(self):
        # Этот метод будет вызываться при изменении вопросов
        if hasattr(self, 'exam_content'):
            self.exam_content.reset_session()
        if hasattr(self, 'edit_content'):
            self.edit_content.load_questions()
        if hasattr(self, 'add_content'):
            # Очищаем форму добавления вопроса
            self.add_content.question_input.text = ''
            for checkbox, text_input in self.add_content.option_widgets:
                checkbox.active = False
                text_input.text = ''
            # Оставляем только два варианта
            while len(self.add_content.option_widgets) > 2:
                self.add_content.remove_option(None)

    @staticmethod
    def show_popup(title, message):
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10))
        popup_layout.add_widget(Label(text=message, font_size=dp(16)))
        close_btn = Button(text='OK', size_hint_y=None, height=dp(40), font_size=dp(16))
        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup_layout.add_widget(close_btn)
        popup.open()


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

    def add_option(self, _instance=None):
        if len(self.option_widgets) >= 6:
            self.show_popup(POPUP_TITLE_INFO, "Максимальное количество вариантов - 6")
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

    def remove_option(self, _instance):
        if len(self.option_widgets) > 2:
            last_option = self.option_widgets.pop()
            self.options_layout.remove_widget(last_option[0].parent)
        else:
            self.show_popup(POPUP_TITLE_INFO, "Минимальное количество вариантов - 2")

    def save_question(self, _instance):
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
            self.show_popup(POPUP_TITLE_ERROR, "Введите вопрос!")
            return

        if len(options) < 2:
            self.show_popup(POPUP_TITLE_ERROR, "Должно быть хотя бы два варианта ответа!")
            return

        if not correct_options:
            self.show_popup(POPUP_TITLE_ERROR, "Выберите хотя бы один правильный ответ!")
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
            self.show_popup(POPUP_TITLE_ERROR, "Не удалось сохранить вопрос! Проверьте разрешения приложения.")
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

        self.show_popup(POPUP_TITLE_SUCCESS, "Вопрос добавлен!")

    @staticmethod
    def show_popup(title, message):
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
        self.option_labels = None
        self.checkboxes = None
        self.app = app
        self._setup_ui()
        self._initialize_state()
        self.load_question()

    def _setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)

        self._create_question_section()
        self._create_options_section()
        self._create_action_section()

    def _initialize_state(self):
        """Инициализирует состояние экзамена"""
        self.current_question = None
        self.correct_indices = []
        self.checkboxes = []
        self.option_labels = []
        self.used_questions = set()
        self.answered = False
        self.answer_correct = False

    def _create_question_section(self):
        """Создает секцию с вопросом"""
        question_scroll = ScrollView(size_hint_y=None, height=dp(150))
        self.question_label = AutoHeightLabel(
            text='Загрузка вопросов...',
            size_hint_y=None,
            text_size=(Window.width - dp(30), None),
            halign='left',
            valign='top',
            font_size=dp(18),
            bold=True,
            color=(1, 1, 0, 1),
            min_height=dp(150),
            padding_x=dp(10),
            padding_y=dp(10)
        )
        self.question_label.bind(size=self.question_label.setter('text_size'))
        question_scroll.add_widget(self.question_label)
        self.add_widget(question_scroll)

    def _create_options_section(self):
        """Создает секцию с вариантами ответов"""
        # Заголовок вариантов
        options_label = Label(
            text='Выберите все правильные ответы:',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16),
            color=(0, 0, 0, 1)
        )
        self.add_widget(options_label)

        # Прокручиваемая область вариантов
        self.options_scroll = ScrollView(size_hint=(1, 0.6))
        self.options_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.options_scroll.add_widget(self.options_layout)
        self.add_widget(self.options_scroll)

    def _create_action_section(self):
        """Создает секцию с кнопками действий"""
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

    def reset_session(self):
        """Сбрасывает сессию и начинает заново"""
        self.used_questions.clear()
        self.load_question()

    def clear_options(self):
        """Очищает все виджеты и списки вариантов ответов"""
        if hasattr(self, 'options_layout'):
            self.options_layout.clear_widgets()
        self.checkboxes = []
        self.option_labels = []

    def load_question(self):
        """Загружает новый вопрос для экзамена"""
        self._reset_ui_state()

        questions = load_questions()
        if not self._validate_questions_availability(questions):
            return

        if not self._select_question(questions):
            return

        self._display_question()
        self._create_options()

    def _reset_ui_state(self):
        """Сбрасывает состояние UI для нового вопроса"""
        self.clear_options()
        self.answered = False
        self.answer_btn.text = 'Ответить'
        self.answer_btn.disabled = False
        self.status_label.text = ''

    def _validate_questions_availability(self, questions):
        """Проверяет доступность вопросов"""
        if not questions:
            self._show_no_questions_message()
            return False
        return True

    def _show_no_questions_message(self):
        """Показывает сообщение об отсутствии вопросов"""
        self.question_label.text = "В базе нет вопросов! Добавьте вопросы на вкладке 'Добавить вопрос'."
        self.answer_btn.disabled = True

    def _select_question(self, questions):
        """Выбирает случайный вопрос из доступных"""
        available_questions = [q for q in questions if q['question'] not in self.used_questions]

        if not available_questions:
            self._show_all_questions_used_message()
            return False

        self.current_question = random.choice(available_questions)
        self.used_questions.add(self.current_question['question'])
        return True

    def _show_all_questions_used_message(self):
        """Показывает сообщение о том, что все вопросы использованы"""
        self.question_label.text = "Все вопросы закончились! Обновите сессию на вкладке редактирования."
        self.answer_btn.disabled = True

    def _display_question(self):
        """Отображает текст вопроса"""
        if self.current_question:
            self.question_label.text = self.current_question['question']
        else:
            self.question_label.text = "Ошибка загрузки вопроса"

    def _create_options(self):
        """Создает варианты ответов в перемешанном порядке"""
        options_with_indices = list(enumerate(self.current_question['options']))
        random.shuffle(options_with_indices)

        self._calculate_correct_indices(options_with_indices)
        self._create_option_widgets(options_with_indices)

    def _calculate_correct_indices(self, options_with_indices):
        """Вычисляет индексы правильных ответов после перемешивания"""
        original_correct = [int(idx) - 1 for idx in self.current_question['correct']]
        self.correct_indices = []

        for new_index, (original_index, _) in enumerate(options_with_indices):
            if original_index in original_correct:
                self.correct_indices.append(new_index)

    def _create_option_widgets(self, options_with_indices):
        """Создает виджеты для вариантов ответов"""
        for new_index, (_, option_text) in enumerate(options_with_indices):
            self._create_single_option(new_index, option_text)

    def _create_single_option(self, _index, option_text):
        """Создает один вариант ответа с чекбоксом и текстом"""
        option_layout = BoxLayout(size_hint_y=None, height=dp(100), spacing=dp(10))

        checkbox = CheckBox(size_hint_x=0.2)
        checkbox.disabled = self.answered

        label = self._create_option_label(option_text)

        option_layout.add_widget(checkbox)
        option_layout.add_widget(label)
        self.options_layout.add_widget(option_layout)

        self.checkboxes.append(checkbox)
        self.option_labels.append(label)

    def _create_option_label(self, text):
        """Создает метку для варианта ответа с белым фоном"""
        label = AutoHeightLabel(
            text=text,
            text_size=(Window.width - dp(80), None),
            halign='left',
            valign='middle',
            font_size=dp(16),
            color=(0, 0, 0, 1),
            min_height=dp(80),
            padding_x=dp(10)
        )

        # Добавляем белый фон
        with label.canvas.before:
            Color(1, 1, 1, 1)
            label.rect = Rectangle(pos=label.pos, size=label.size)

        label.bind(pos=self.update_label_rect, size=self.update_label_rect)
        label.bind(size=label.setter('text_size'))

        return label

    @staticmethod
    def update_label_rect(instance, _value):
        """Обновляет позицию и размер фона метки"""
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

    def on_answer_btn_press(self, _instance):
        """Обрабатывает нажатие кнопки ответа/продолжения"""
        if not self.answered:
            self.check_answer()
        else:
            self.load_question()

    def check_answer(self):
        """Проверяет выбранные ответы"""
        selected_indices = self._get_selected_indices()

        if not self._validate_selection(selected_indices):
            return

        self._disable_checkboxes()
        self._process_answer(selected_indices)

    def _get_selected_indices(self):
        """Возвращает индексы выбранных ответов"""
        return [i for i, checkbox in enumerate(self.checkboxes) if checkbox.active]

    def _validate_selection(self, selected_indices):
        """Проверяет, что выбран хотя бы один ответ"""
        if not selected_indices:
            self.status_label.text = "Выберите хотя бы один ответ!"
            self.status_label.color = (1, 0, 0, 1)
            return False
        return True

    def _disable_checkboxes(self):
        """Блокирует чекбоксы после ответа"""
        for checkbox in self.checkboxes:
            checkbox.disabled = True

    def _process_answer(self, selected_indices):
        """Обрабатывает ответ пользователя"""
        self.answered = True
        self.answer_btn.text = 'Далее'

        if set(selected_indices) == set(self.correct_indices):
            self._handle_correct_answer()
        else:
            self._handle_incorrect_answer(selected_indices)

    def _handle_correct_answer(self):
        """Обрабатывает правильный ответ"""
        self.status_label.text = "Правильно!"
        self.status_label.color = (0, 1, 0, 1)
        self.answer_correct = True
        self._highlight_answers(self.correct_indices, (0.7, 1, 0.7, 1))

    def _handle_incorrect_answer(self, selected_indices):
        """Обрабатывает неправильный ответ"""
        self.status_label.text = "Неправильно!"
        self.status_label.color = (1, 0, 0, 1)
        self.answer_correct = False

        # Подсвечиваем неправильно выбранные ответы
        incorrect_selected = [i for i in selected_indices if i not in self.correct_indices]
        self._highlight_answers(incorrect_selected, (1, 0.7, 0.7, 1))

        # Подсвечиваем правильные ответы
        self._highlight_answers(self.correct_indices, (0.7, 1, 0.7, 1))

    def _highlight_answers(self, indices, color):
        """Подсвечивает ответы указанным цветом"""
        for i in indices:
            self._highlight_single_answer(i, color)

    def _highlight_single_answer(self, index, color):
        """Подсвечивает один ответ указанным цветом"""
        self.option_labels[index].canvas.before.clear()
        with self.option_labels[index].canvas.before:
            Color(*color)
            Rectangle(pos=self.option_labels[index].pos, size=self.option_labels[index].size)


class EditQuestionsTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.current_edit_index = None
        self._edit_popup_data = {}  # Инициализируем пустой словарь
        self._setup_ui()
        self.load_questions()

    def _setup_ui(self):
        """Настраивает пользовательский интерфейс вкладки"""
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)

        self._create_title()
        self._create_questions_list()
        self._create_control_buttons()

    def _create_title(self):
        """Создает заголовок вкладки"""
        title_label = Label(
            text='Редактирование вопросов',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(20),
            bold=True
        )
        self.add_widget(title_label)

    def _create_questions_list(self):
        """Создает прокручиваемый список вопросов"""
        self.questions_scroll = ScrollView(size_hint=(1, 0.6))
        self.questions_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.questions_layout.bind(minimum_height=self.questions_layout.setter('height'))
        self.questions_scroll.add_widget(self.questions_layout)
        self.add_widget(self.questions_scroll)

    def _create_control_buttons(self):
        """Создает кнопки управления"""
        self._create_refresh_button()
        self._create_export_import_buttons()
        self._create_session_buttons()

    def _create_refresh_button(self):
        """Создает кнопку обновления списка"""
        self.refresh_btn = Button(
            text='Обновить список',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(14)
        )
        self.refresh_btn.bind(on_press=self.load_questions)
        self.add_widget(self.refresh_btn)

    def _create_export_import_buttons(self):
        """Создает кнопки экспорта и импорта"""
        export_import_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))

        self.export_btn = Button(text='Экспорт', size_hint_x=0.5, font_size=dp(12))
        self.export_btn.bind(on_press=self.export_database)
        export_import_layout.add_widget(self.export_btn)

        self.import_btn = Button(text='Импорт', size_hint_x=0.5, font_size=dp(12))
        self.import_btn.bind(on_press=self.import_database)
        export_import_layout.add_widget(self.import_btn)

        self.add_widget(export_import_layout)

    def _create_session_buttons(self):
        """Создает кнопки управления сессией"""
        self.reset_session_btn = Button(
            text='Сбросить сессию',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(12)
        )
        self.reset_session_btn.bind(on_press=self.reset_exam_session)
        self.add_widget(self.reset_session_btn)

        self.check_db_btn = Button(
            text='Проверить состояние базы',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(12)
        )
        self.check_db_btn.bind(on_press=self.check_database_status)
        self.add_widget(self.check_db_btn)

    def load_questions(self, _instance=None):
        """Загружает и отображает список вопросов"""
        self.questions_layout.clear_widgets()
        questions = load_questions()

        if not questions:
            self._show_no_questions_message()
            return

        self._display_questions_list(questions)

    def _show_no_questions_message(self):
        """Показывает сообщение об отсутствии вопросов"""
        no_questions_label = Label(
            text='В базе нет вопросов.',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(16)
        )
        self.questions_layout.add_widget(no_questions_label)

    def _display_questions_list(self, questions):
        """Отображает список вопросов с кнопками управления"""
        for idx, question in enumerate(questions):
            self._create_question_item(idx, question)

    def _create_question_item(self, index, question):
        """Создает элемент списка для одного вопроса"""
        question_item = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))

        # Текст вопроса
        question_text = self._truncate_question_text(question['question'])
        question_label = Label(
            text=question_text,
            size_hint_x=0.7,
            text_size=(Window.width * 0.7 - dp(20), None),
            halign='left',
            valign='middle'
        )
        question_label.bind(size=question_label.setter('text_size'))

        # Кнопки управления
        btn_layout = self._create_question_buttons(index, question)

        question_item.add_widget(question_label)
        question_item.add_widget(btn_layout)
        self.questions_layout.add_widget(question_item)

    @staticmethod
    def _truncate_question_text(text):
        """Обрезает длинный текст вопроса"""
        return text[:37] + '...' if len(text) > 40 else text

    def _create_question_buttons(self, index, _question):
        """Создает кнопки управления для вопроса"""
        btn_layout = BoxLayout(size_hint_x=0.3, spacing=dp(2))

        edit_btn = Button(text='Ред.', size_hint_x=0.5, font_size=dp(12))
        edit_btn.bind(on_press=lambda inst: self.edit_question(index, load_questions()))

        delete_btn = Button(text='Удл.', size_hint_x=0.5, font_size=dp(12))
        delete_btn.bind(on_press=lambda inst: self.delete_question(index, load_questions()))

        btn_layout.add_widget(edit_btn)
        btn_layout.add_widget(delete_btn)

        return btn_layout

    def edit_question(self, index, questions):
        """Открывает попап редактирования вопроса"""
        self.current_edit_index = index
        question_data = questions[index]

        # Создаем попап для редактирования
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        popup = Popup(title='Редактирование вопроса', content=popup_layout,
                      size_hint=(0.95, 0.9))

        # Инициализируем данные попапа
        self._edit_popup_data = {
            'popup': popup,
            'option_widgets': [],
            'options_layout': None
        }

        # Создаем содержимое попапа
        question_input = self._create_question_input(question_data['question'])
        popup_layout.add_widget(Label(text='Вопрос:', size_hint_y=None, height=dp(30)))
        popup_layout.add_widget(question_input)

        # Создаем секцию вариантов ответов
        _, options_layout = self._create_options_section(popup_layout, question_data)
        self._edit_popup_data['options_layout'] = options_layout

        # Создаем кнопки управления
        self._create_edit_buttons(popup_layout, question_input)

        popup.open()

    @staticmethod
    def _create_question_input(question_text):
        """Создает поле ввода для вопроса"""
        return AutoHeightTextInput(
            text=question_text,
            multiline=True,
            size_hint_y=None,
            min_height=dp(40),
            font_size=dp(14)
        )

    def _create_options_section(self, popup_layout, question_data):
        """Создает секцию вариантов ответов"""
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

        # Добавляем существующие варианты ответов
        for i, option in enumerate(question_data['options']):
            self._add_option_widget(option, i, question_data, options_layout)

        return options_scroll, options_layout

    def _add_option_widget(self, option_text, index, question_data, options_layout):
        """Добавляет виджет варианта ответа"""
        option_layout = BoxLayout(size_hint_y=None, height=dp(60))

        checkbox = CheckBox(size_hint_x=0.2)
        if str(index + 1) in question_data['correct']:
            checkbox.active = True

        text_input = AutoHeightTextInput(
            text=option_text,
            multiline=True,
            size_hint_x=0.8,
            min_height=dp(40),
            font_size=dp(14)
        )

        option_layout.add_widget(checkbox)
        option_layout.add_widget(text_input)
        options_layout.add_widget(option_layout)
        self._edit_popup_data['option_widgets'].append((checkbox, text_input))

    def _create_edit_buttons(self, popup_layout, question_input):
        """Создает кнопки управления попапом"""
        # Кнопки управления вариантами
        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))

        add_btn = Button(text='Добавить', font_size=dp(12))
        remove_btn = Button(text='Удалить', font_size=dp(12))

        add_btn.bind(on_press=lambda x: self._on_add_option())
        remove_btn.bind(on_press=lambda x: self._on_remove_option())

        btn_layout.add_widget(add_btn)
        btn_layout.add_widget(remove_btn)
        popup_layout.add_widget(btn_layout)

        # Кнопки сохранения и отмены
        btn_layout2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        save_btn = Button(text='Сохранить', font_size=dp(14))
        cancel_btn = Button(text='Отмена', font_size=dp(14))

        save_btn.bind(on_press=lambda x: self._save_question(question_input))
        cancel_btn.bind(on_press=lambda x: self._edit_popup_data['popup'].dismiss())

        btn_layout2.add_widget(save_btn)
        btn_layout2.add_widget(cancel_btn)
        popup_layout.add_widget(btn_layout2)

    def _on_add_option(self):
        """Обработчик добавления варианта"""
        if len(self._edit_popup_data['option_widgets']) >= 6:
            self.show_popup(POPUP_TITLE_INFO, "Максимальное количество вариантов - 6")
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
        self._edit_popup_data['options_layout'].add_widget(option_layout)
        self._edit_popup_data['option_widgets'].append((checkbox, text_input))

    def _on_remove_option(self):
        """Обработчик удаления варианта"""
        if len(self._edit_popup_data['option_widgets']) > 2:
            last_option = self._edit_popup_data['option_widgets'].pop()
            self._edit_popup_data['options_layout'].remove_widget(last_option[0].parent)
        else:
            self.show_popup(POPUP_TITLE_INFO, "Минимальное количество вариантов - 2")

    def _save_question(self, question_input):
        """Сохраняет отредактированный вопрос"""
        if not hasattr(self, '_edit_popup_data') or not self._edit_popup_data:
            self.show_popup(POPUP_TITLE_ERROR, "Данные редактирования не найдены")
            return

        questions = load_questions()
        question_text = question_input.text.strip()
        options_data = self._collect_options_data()

        if not self._validate_question_data(question_text, options_data):
            return

        # Обновляем вопрос
        questions[self.current_edit_index] = {
            'question': question_text,
            'options': options_data['options'],
            'correct': options_data['correct_options']
        }

        if save_questions(questions):
            self._edit_popup_data['popup'].dismiss()
            self.load_questions()
            self.app.update_questions()
            self.show_popup(POPUP_TITLE_SUCCESS, "Вопрос обновлен!")
        else:
            self.show_popup(POPUP_TITLE_ERROR, "Не удалось сохранить вопросы!")

    def _collect_options_data(self):
        """Собирает данные о вариантах ответов"""
        options = []
        correct_options = []

        for i, (checkbox, text_input) in enumerate(self._edit_popup_data['option_widgets']):
            option_text = text_input.text.strip()
            if option_text:
                options.append(option_text)
                if checkbox.active:
                    correct_options.append(str(i + 1))

        return {'options': options, 'correct_options': correct_options}

    def _validate_question_data(self, question_text, options_data):
        """Проверяет валидность данных вопроса"""
        if not question_text:
            self.show_popup(POPUP_TITLE_ERROR, "Введите вопрос!")
            return False

        if len(options_data['options']) < 2:
            self.show_popup(POPUP_TITLE_ERROR, "Должно быть хотя бы два варианта ответа!")
            return False

        if not options_data['correct_options']:
            self.show_popup(POPUP_TITLE_ERROR, "Выберите хотя бы один правильный ответ!")
            return False

        return True

    # Остальные методы остаются без изменений
    def delete_question(self, index, questions):
        """Удаляет вопрос с подтверждением"""
        if 0 <= index < len(questions):
            self._show_delete_confirmation(index, questions)

    def _show_delete_confirmation(self, index, questions):
        """Показывает подтверждение удаления"""
        confirm_layout = BoxLayout(orientation='vertical', padding=dp(10))
        confirm_label = Label(
            text=f'Вы уверены, что хотите удалить вопрос?\n\n{questions[index]["question"][:50]}...',
            text_size=(Window.width * 0.8 - dp(20), None)
        )
        confirm_layout.add_widget(confirm_label)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        yes_btn = Button(text='Да', font_size=dp(16))
        no_btn = Button(text='Нет', font_size=dp(16))

        # Создаем попап перед привязкой кнопок
        confirm_popup = Popup(title='Подтверждение удаления', content=confirm_layout, size_hint=(0.8, 0.4))

        # Правильная привязка кнопок
        yes_btn.bind(on_press=lambda x: self._confirm_delete(index, questions, confirm_popup))
        no_btn.bind(on_press=confirm_popup.dismiss)

        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        confirm_layout.add_widget(btn_layout)

        confirm_popup.open()

    def _confirm_delete(self, index, questions, popup):
        """Подтверждает удаление вопроса"""
        questions.pop(index)

        if save_questions(questions):
            popup.dismiss()  # Используем переданный попап
            self.load_questions()
            self.app.update_questions()
            self.show_popup(POPUP_TITLE_SUCCESS, "Вопрос удален!")
        else:
            self.show_popup(POPUP_TITLE_ERROR, "Не удалось сохранить вопросы!")

    def reset_exam_session(self, _instance):
        """Сбрасывает сессию экзамена"""
        if hasattr(self.app, 'exam_content'):
            self.app.exam_content.reset_session()
            self.show_popup(POPUP_TITLE_SUCCESS, "Сессия экзамена сброшена!")

    def check_database_status(self, _instance):
        """Проверяет состояние базы данных"""
        questions = load_questions()
        db_path = QUESTIONS_FILE
        db_exists = os.path.exists(db_path)
        db_size = os.path.getsize(db_path) if db_exists else 0

        message = f"""Путь к базе: {db_path}
Файл существует: {'Да' if db_exists else 'Нет'}
Размер файла: {db_size} байт
Количество вопросов: {len(questions)}"""

        self.show_popup("Состояние базы данных", message)

    def export_database(self, _instance):
        """Экспортирует базу данных"""
        try:
            questions = load_questions()
            if not questions:
                self.show_popup(POPUP_TITLE_ERROR, "Нет вопросов для экспорта")
                return

            if platform == 'android':
                self._export_android(questions)
            else:
                self._export_desktop(questions)
        except Exception as ex:
            self.show_popup(POPUP_TITLE_ERROR, f"Ошибка экспорта: {str(ex)}")

    def import_database(self, _instance):
        """Импортирует базу данных"""
        try:
            if platform == 'android':
                self._import_android()
            else:
                self._import_desktop()
        except Exception as ex:
            self.show_popup(POPUP_TITLE_ERROR, f"Ошибка импорта: {str(ex)}")

    def _export_android(self, questions):
        """Экспорт для Android"""
        from android.storage import primary_external_storage_path  # type: ignore
        downloads_path = os.path.join(primary_external_storage_path(), "Download")
        export_path = os.path.join(downloads_path, "questions_export.json")

        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path)

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        self.show_popup(POPUP_TITLE_SUCCESS, f"База экспортирована в:\n{export_path}")

    def _export_desktop(self, questions):
        """Экспорт для Desktop"""
        home_dir = os.path.expanduser("~")
        downloads_path = os.path.join(home_dir, 'Downloads')

        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path)

        export_path = os.path.join(downloads_path, 'questions_export.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        self.show_popup(POPUP_TITLE_SUCCESS, f"База экспортирована в:\n{export_path}")

    def _import_android(self):
        """Импорт для Android"""
        from android.storage import primary_external_storage_path  # type: ignore
        downloads_path = os.path.join(primary_external_storage_path(), "Download")
        import_path = os.path.join(downloads_path, "questions_export.json")

        if not os.path.exists(import_path):
            self.show_popup(POPUP_TITLE_ERROR, "Файл questions_export.json не найден")
            return

        self._import_questions_from_file(import_path)

    def _import_desktop(self):
        """Импорт для Desktop"""
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        downloads_path = os.path.join(os.path.expanduser("~"), 'Downloads')
        file_path = filedialog.askopenfilename(
            initialdir=downloads_path,
            title="Выберите файл с вопросами",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        root.destroy()

        if not file_path:
            return

        self._import_questions_from_file(file_path)

    def _import_questions_from_file(self, file_path):
        """Импортирует вопросы из файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            imported_questions = json.load(f)

        if not self._validate_imported_questions(imported_questions):
            return

        if save_questions(imported_questions):
            self.show_popup(POPUP_TITLE_SUCCESS, f"Импортировано {len(imported_questions)} вопросов")
            self.app.update_questions()
            self.load_questions()
        else:
            self.show_popup(POPUP_TITLE_ERROR, "Ошибка сохранения импортированной базы")

    def _validate_imported_questions(self, imported_questions):
        """Проверяет валидность импортированных вопросов"""
        if not isinstance(imported_questions, list):
            self.show_popup(POPUP_TITLE_ERROR, "Некорректный формат файла")
            return False

        valid_questions = [q for q in imported_questions if
                           isinstance(q, dict) and
                           'question' in q and
                           'options' in q and
                           'correct' in q]

        if not valid_questions:
            self.show_popup(POPUP_TITLE_ERROR, "Нет валидных вопросов в файле")
            return False

        return True

    @staticmethod
    def show_popup(title, message):
        """Показывает всплывающее окно с сообщением"""
        popup_layout = BoxLayout(orientation='vertical', padding=dp(10))

        # Создаем ScrollView для длинных сообщений
        scroll = ScrollView(size_hint=(1, 0.8))
        label = Label(
            text=message,
            font_size=dp(14),
            text_size=(Window.width * 0.7, None),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        label.bind(texture_size=label.setter('size'))
        scroll.add_widget(label)
        popup_layout.add_widget(scroll)

        # Кнопка закрытия
        close_btn = Button(text='OK', size_hint_y=None, height=dp(40), font_size=dp(16))
        popup_layout.add_widget(close_btn)

        # Создаем попап
        popup = Popup(title=title, content=popup_layout, size_hint=(0.9, 0.7))

        # Правильная привязка кнопки закрытия
        close_btn.bind(on_press=popup.dismiss)

        popup.open()
        return popup  # Возвращаем ссылку на попап


if __name__ == '__main__':
    ExamApp().run()
