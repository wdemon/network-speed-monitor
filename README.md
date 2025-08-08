
📡 Network Speed Monitor
Простой и автономный монитор скорости интернета с веб-интерфейсом, графиками и PDF-отчетами.

<img width="1143" height="779" alt="image" src="https://github.com/user-attachments/assets/58cc35ba-a2fa-45b9-8a2c-c4f073eee31f" />


⚙️ Возможности
Регулярные измерения скорости: загрузка, отдача, пинг

Сохранение истории по дням в формате JSON

Визуализация через графики и таблицы (веб-интерфейс)

Ручной запуск тестов и автообновление статистики

Выгрузка PDF-отчетов

Настройки через UI

Fallback на CLI Ookla speedtest при недоступности Python API

📦 Установка
Рекомендуется запуск в отдельной виртуальной среде:

bash
Копировать
Редактировать
# Клонировать репозиторий
git clone https://github.com/yourusername/network-speed-monitor.git
cd network-speed-monitor

# Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate    # для Linux/macOS
venv\Scripts\activate.bat   # для Windows

# Установить зависимости
pip install -r requirements.txt
⚠️ Дополнительно: установить CLI от Ookla (по желанию, для fallback):

https://www.speedtest.net/apps/cli

🚀 Запуск
Фоновый мониторинг (запускает тесты по расписанию):
bash
Копировать
Редактировать
python speed_monitor.py
Веб-интерфейс (Flask + Socket.IO):
bash
Копировать
Редактировать
python web_dashboard.py
По умолчанию будет доступен по адресу: http://localhost:8080

🔧 Настройки
Настройки хранятся в settings.json (создаётся автоматически при первом запуске) и доступны через UI.
Параметры:

Частота измерений (интервал)

Пороговые значения скорости/пинга

Автообновление графиков

Язык отчета (RU/EN)

📁 Хранилище данных
Все результаты сохраняются в директорию speed_data/ в формате YYYY-MM-DD.json

Очистка старых файлов — автоматическая (по умолчанию: старше 30 дней)

📜 Лицензия
MIT License — свободное использование и модификация.

