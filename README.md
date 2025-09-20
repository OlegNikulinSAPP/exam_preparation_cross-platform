# Exam Preparation App
## Кроссплатформенное приложение для подготовки к экзаменам с системой вопросов и ответов.

###Функционал

📝 Добавление и редактирование вопросов с множественным выбором

🎯 Режим экзамена со случайными вопросами

📊 Отслеживание прогресса обучения

📱 Поддержка Android и Desktop платформ

🔄 Импорт/экспорт базы данных

### Структура проекта
```text
exam_preparation_cross-platform/
├── main.py              # Основной файл приложения
├── buildozer.spec       # Конфигурация сборки для Android
├── colab.txt           # Скрипт сборки в Google Colab
├── questions.json      # База данных вопросов (создается автоматически)
└── README.md           # Документация
````

## Установка и запуск
### Локальная разработка
````bash
# Установите зависимости
pip install kivy

# Запустите приложение
python main.py
````
## Сборка для Android
### Для сборки APK используйте Google Colab и скрипт из файла colab.txt.

## Работа с базой данных
## Экспорт базы данных на компьютер
```bash
adb exec-out run-as org.test.myapp cat files/data/questions.json > C:\Users\Locadm\Desktop\questions_backup.json
```

## Импорт базы данных в приложение
```bash
# Скопируйте файл с рабочего стола на устройство
adb push "C:\Users\Locadm\Desktop\questions.json" /sdcard/temp_questions.json

# Скопируйте файл в папку приложения
adb shell cat /sdcard/temp_questions.json > temp_file.json
adb push temp_file.json /data/local/tmp/
adb shell run-as org.test.myapp cp /data/local/tmp/temp_file.json files/data/questions.json

# Очистка временных файлов
adb shell rm /data/local/tmp/temp_file.json
adb shell rm /sdcard/temp_questions.json
del temp_file.json
```
## Проверка базы данных
```bash
# Проверьте размер и дату изменения файла
adb shell run-as org.test.myapp ls -la files/data/questions.json

# Посмотрите начало файла для проверки содержимого
adb shell run-as org.test.myapp head -n 5 files/data/questions.json
```
## Сборка в Google Colab
### Скопируйте содержимое файла colab.txt в ячейку Google Colab и выполните:

Откройте Google Colab

Создайте новый ноутбук

Вставьте содержимое colab.txt в ячейку

Запустите выполнение ячейки

После завершения сборки APK файл будет автоматически скачан.

## Важные замечания
Для работы с ADB убедитесь, что:

Включена отладка по USB на устройстве

Установлены драйверы Android ADB на компьютере

Устройство подключено по USB и разрешена отладка

Идентификатор пакета (org.test.myapp) может отличаться в зависимости от настроек в buildozer.spec

На Android 10+ могут потребоваться дополнительные разрешения для доступа к файловой системе

## Поддержка
При возникновении проблем:

Проверьте логи сборки в Colab

Убедитесь в правильности настроек в buildozer.spec

Проверьте подключение устройства и настройки отладки по USB

## Лицензия
Проект распространяется под лицензией MIT.