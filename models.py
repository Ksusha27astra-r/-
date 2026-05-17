from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from enum import Enum
import json

db = SQLAlchemy()
class Eventstat(Enum):
    scoro = "скоро"
    vip = "выполнено"
    prosroch = "просрочено"
class Eventyp(Enum):
    visit = "Визит к врачу"
    analiz = "Анализ"
    yzi = "УЗИ"
    test = "Тест/Анализ"
class Trimester(Enum):
    f = 1
    s = 2
    t = 3

class Userprofile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    conception_date = db.Column(db.Date, nullable=False)
    has_health_issues = db.Column(db.Boolean, default=False)
    health_conditions = db.Column(db.Text, default='[]')
    needs_perinatologist = db.Column(db.Boolean, default=False)
    joined_week = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_current_week(self):
        today = date.today()
        days_diff = (today - self.conception_date).days
        week = days_diff // 7
        return max(0, min(42, week))

    def get_trimester(self, week=None):
        if week is None:
            week = self.calculate_current_week()
        if week <= 13:
            return Trimester.f
        elif week <= 27:
            return Trimester.s
        else:
            return Trimester.t
    def get_health_conditions_list(self):
        return json.loads(self.health_conditions) if self.health_conditions else []
    def set_health_conditions(self, conditions_list):
        self.health_conditions = json.dumps(conditions_list, ensure_ascii=False)
        self.needs_perinatologist = len(conditions_list) > 0
class Pregnancyevent(db.Model):
    __tablename__ = 'pregnancy_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'))
    title = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    week_of_pregnancy = db.Column(db.Integer, nullable=False)
    scheduled_date = db.Column(db.Date, nullable=True)
    deadline_week = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text)
    is_completed = db.Column(db.Boolean, default=False)
    is_critical = db.Column(db.Boolean, default=False)
    warning_message = db.Column(db.Text, nullable=True)
    action_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('Userprofile', backref='events')
    def get_status(self, current_week):
        if self.is_completed:
            return Eventstat.vip.value
        if self.deadline_week and current_week > self.deadline_week:
            return Eventstat.prosroch.value
        elif self.week_of_pregnancy < current_week:
            return Eventstat.prosroch.value
        else:
            return Eventstat.scoro.value
    def to_dict(self, current_week):
        status = self.get_status(current_week)
        return {
            'id': self.id,
            'title': self.title,
            'event_type': self.event_type,
            'week': self.week_of_pregnancy,
            'deadline_week': self.deadline_week,
            'date': self.scheduled_date.strftime('%Y-%m-%d') if self.scheduled_date else None,
            'description': self.description,
            'status': status,
            'completed': self.is_completed,
            'is_critical': self.is_critical,
            'warning_message': self.warning_message if status == 'просрочено' else None,
            'action_message': self.action_message if status == 'просрочено' else None
        }
listdoctors = {
    "Гипертония (высокое давление)": {"doctor": "Кардиолог", "week": 10, "frequency": "регулярно"},
    "Пороки сердца": {"doctor": "Кардиолог", "week": 10, "frequency": "регулярно"},
    "Нарушения ритма сердца": {"doctor": "Кардиолог", "week": 10, "frequency": "регулярно"},
    "Анемия (низкий гемоглобин)": {"doctor": "Гематолог", "week": 10, "frequency": "регулярно"},
    "Тромбофилия": {"doctor": "Гематолог", "week": 10, "frequency": "регулярно"},
    "Резус-конфликт": {"doctor": "Гематолог", "week": 8, "frequency": "регулярно"},
    "Хронический пиелонефрит": {"doctor": "Нефролог/Уролог", "week": 10, "frequency": "регулярно"},
    "Цистит": {"doctor": "Нефролог/Уролог", "week": 10, "frequency": "по необходимости"},
    "Сильные мигрени": {"doctor": "Невролог", "week": 10, "frequency": "по необходимости"},
    "Эпилепсия": {"doctor": "Невролог", "week": 8, "frequency": "регулярно"},
    "Боли в спине": {"doctor": "Невролог", "week": 10, "frequency": "по необходимости"},
    "Возраст матери старше 35 лет": {"doctor": "Генетик", "week": 12, "frequency": "1-2 раза"},
    "Сильный токсикоз": {"doctor": "Гастроэнтеролог", "week": 8, "frequency": "по необходимости"},
    "Гастрит": {"doctor": "Гастроэнтеролог", "week": 10, "frequency": "регулярно"},
    "Проблемы с печенью": {"doctor": "Гастроэнтеролог", "week": 10, "frequency": "регулярно"},
    "Проблемы с желчным пузырем": {"doctor": "Гастроэнтеролог", "week": 10, "frequency": "регулярно"},
    "TORCH-комплекс": {"doctor": "Инфекционист", "week": 8, "frequency": "1 раз"},
    "Гепатиты": {"doctor": "Инфекционист", "week": 8, "frequency": "регулярно"},
    "Герпес": {"doctor": "Инфекционист", "week": 8, "frequency": "по необходимости"},
    "Выраженный варикоз": {"doctor": "Флеболог", "week": 20, "frequency": "регулярно"},
    "Риск тромбоза": {"doctor": "Флеболог", "week": 20, "frequency": "регулярно"},
}
class Eventgenerator:
    @staticmethod
    def get_all_available_health_issues():
        """Получить список возможных проблем со здоровьем"""
        return [
            {"id": "hypertension", "name": "Гипертония (высокое давление)", "doctor": "Кардиолог"},
            {"id": "heart_defects", "name": "Пороки сердца", "doctor": "Кардиолог"},
            {"id": "arrhythmia", "name": "Нарушения ритма сердца", "doctor": "Кардиолог"},
            {"id": "anemia", "name": "Анемия (низкий гемоглобин)", "doctor": "Гематолог"},
            {"id": "thrombophilia", "name": "Тромбофилия", "doctor": "Гематолог"},
            {"id": "rhesus_conflict", "name": "Резус-конфликт", "doctor": "Гематолог"},
            {"id": "pyelonephritis", "name": "Хронический пиелонефрит", "doctor": "Нефролог/Уролог"},
            {"id": "cystitis", "name": "Цистит", "doctor": "Нефролог/Уролог"},
            {"id": "migraine", "name": "Сильные мигрени", "doctor": "Невролог"},
            {"id": "epilepsy", "name": "Эпилепсия", "doctor": "Невролог"},
            {"id": "back_pain", "name": "Боли в спине", "doctor": "Невролог"},
            {"id": "age_over_35", "name": "Возраст матери старше 35 лет", "doctor": "Генетик"},
            {"id": "toxicosis", "name": "Сильный токсикоз", "doctor": "Гастроэнтеролог"},
            {"id": "gastritis", "name": "Гастрит", "doctor": "Гастроэнтеролог"},
            {"id": "liver_problems", "name": "Проблемы с печенью", "doctor": "Гастроэнтеролог"},
            {"id": "gallbladder_problems", "name": "Проблемы с желчным пузырем", "doctor": "Гастроэнтеролог"},
            {"id": "torch", "name": "TORCH-комплекс", "doctor": "Инфекционист"},
            {"id": "hepatitis", "name": "Гепатиты", "doctor": "Инфекционист"},
            {"id": "herpes", "name": "Герпес", "doctor": "Инфекционист"},
            {"id": "varicose", "name": "Выраженный варикоз", "doctor": "Флеболог"},
            {"id": "thrombosis_risk", "name": "Риск тромбоза", "doctor": "Флеболог"},
        ]
    @staticmethod
    def generate_standard_events(user, current_week):
        """Генерация стандартных событий на основе недели"""
        events = []
        if current_week <= 14:
            standard_doctors = [
                {"title": "Прием терапевта (первичный)", "week": 10, "deadline": 14, "critical": False},
                {"title": "Прием стоматолога (первичный)", "week": 8, "deadline": 14, "critical": False},
                {"title": "Прием офтальмолога (первичный)", "week": 8, "deadline": 14, "critical": False},
                {"title": "Прием ЛОРа", "week": 10, "deadline": 14, "critical": True},
                {"title": "Прием хирурга", "week": 10, "deadline": 14, "critical": False},
                {"title": "Прием эндокринолога", "week": 10, "deadline": 14, "critical": False},
            ]
            for doc in standard_doctors:
                events.append({
                    "title": doc["title"],
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": doc["week"],
                    "deadline_week": doc["deadline"],
                    "is_critical": doc["critical"],
                    "description": f"Обязательный осмотр до {doc['deadline']} недель",
                    "warning_message": f"Обязательно посетить до {doc['deadline']} недель(и) беременности",
                    "action_message": "Срочно запишитесь к врачу!"
                })
            events.append({
                "title": "Первый скрининг (УЗИ + PAPP-A/ХГЧ)",
                "event_type": Eventyp.yzi.value,
                "week_of_pregnancy": 12,
                "deadline_week": 14,
                "is_critical": True,
                "description": "Скрининг первого триместра",
                "warning_message": "КРИТИЧНО! Первый скрининг делается строго с 11 по 13.6 недель!",
                "action_message": "Если срок уже 14+ недель - сделайте НИПТ (неинвазивный пренатальный тест)"
            })
            first_trimester_tests = [
                {"title": "Общий анализ крови", "week": 8},
                {"title": "Тест на резус-фактор", "week": 6},
                {"title": "Биохимический анализ крови", "week": 8},
                {"title": "Коагулограмма (свертываемость крови)", "week": 8},
                {"title": "Антитела к краснухе (TORCH-комплекс)", "week": 8},
                {"title": "Анализы на сифилис, гепатиты В и С, ВИЧ", "week": 8},
                {"title": "Мазок на влагалищную флору", "week": 8},
                {"title": "Посев мочи на микрофлору", "week": 8},
                {"title": "ЭКГ", "week": 8},
                {"title": "УЗИ почек", "week": 8},
            ]
            for test in first_trimester_tests:
                events.append({
                    "title": test["title"],
                    "event_type": Eventyp.analiz.value,
                    "week_of_pregnancy": test["week"],
                    "deadline_week": 14,
                    "is_critical": False,
                    "description": f"Анализ I триместра",
                    "warning_message": "Пропущен первый визит и анализы крови: просто сдайте их сейчас. Группа крови и инфекции не меняются, их важно знать для безопасности родов.",
                    "action_message": "Сдайте анализы в ближайшее время"
                })
        if 14 <= current_week <= 27:
            if current_week >= 16:
                events.append({
                    "title": "Тройной тест (АФП + ХГ + НЭ)",
                    "event_type": Eventyp.analiz.value,
                    "week_of_pregnancy": 17,
                    "deadline_week": 18,
                    "is_critical": True,
                    "description": "Исследование уровня альфа-фетопротеина (АФП), ХГЧ, неконъюгированного эстриола (НЭ)",
                    "warning_message": "Если показатели повышены - после УЗИ вас направят на медико-генетическое консультирование",
                    "action_message": "Сдайте анализы немедленно"
                })
            if current_week >= 19:
                events.append({
                    "title": "Второе УЗИ (скрининг II триместра)",
                    "event_type": Eventyp.yzi.value,
                    "week_of_pregnancy": 20,
                    "deadline_week": 21,
                    "is_critical": True,
                    "description": "Детальный осмотр анатомии плода",
                    "warning_message": "Критично! Пропущено УЗИ второго скрининга!",
                    "action_message": "Записаться на «экспертное УЗИ» немедленно. Даже на 23-25 неделе врач сможет увидеть большинство пороков развития"
                })
            if current_week >= 24:
                events.append({
                    "title": "Глюкозотолерантный тест (ГТТ)",
                    "event_type": Eventyp.analiz.value,
                    "week_of_pregnancy": 26,
                    "deadline_week": 28,
                    "is_critical": False,
                    "description": "Тест на гестационный диабет",
                    "warning_message": "Пропущен ГТТ!",
                    "action_message": "Если срок 29-30 недель - тест еще могут разрешить. Если позже - сдайте кровь на гликированный гемоглобин"
                })
            events.append({
                "title": "Визит к акушеру-гинекологу (плановый)",
                "event_type": Eventyp.visit.value,
                "week_of_pregnancy": current_week,
                "deadline_week": current_week + 2,
                "is_critical": False,
                "description": "Каждые 2-3 недели посещать врача + сдавать анализ крови и мочи",
                "warning_message": "Пропущен плановый визит к врачу",
                "action_message": "Запишитесь к врачу в ближайшее время"
            })
        if current_week >= 28:
            if current_week >= 30:
                events.append({
                    "title": "Прием терапевта (повторный)",
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": 30,
                    "deadline_week": 32,
                    "is_critical": False,
                    "description": "Второй осмотр терапевта перед декретом",
                    "warning_message": "Пропущен визит к терапевту",
                    "action_message": "Срочно запишитесь к врачу"
                })
            if current_week >= 32:
                events.append({
                    "title": "Прием стоматолога (повторный)",
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": 34,
                    "deadline_week": 36,
                    "is_critical": False,
                    "description": "Повторный осмотр стоматолога",
                    "warning_message": "Пропущен повторный визит к стоматологу",
                    "action_message": "Запишитесь к стоматологу"
                })
            if current_week >= 35:
                events.append({
                    "title": "Прием офтальмолога (повторный)",
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": 35,
                    "deadline_week": 36,
                    "is_critical": False,
                    "description": "Повторный осмотр окулиста",
                    "warning_message": "Пропущен повторный визит к окулисту",
                    "action_message": "Запишитесь к окулисту"
                })
            events.append({
                "title": "Третье УЗИ с доплерометрией",
                "event_type": Eventyp.yzi.value,
                "week_of_pregnancy": 32,
                "deadline_week": 34,
                "is_critical": True,
                "description": "Последнее плановое УЗИ",
                "warning_message": "Пропущено третье УЗИ!",
                "action_message": "Срочно запишитесь на УЗИ с доплерометрией"
            })
            if current_week >= 32:
                events.append({
                    "title": "КТГ (кардиотокография)",
                    "event_type": Eventyp.test.value,
                    "week_of_pregnancy": 33,
                    "deadline_week": 34,
                    "is_critical": False,
                    "description": "Запись сердцебиения плода",
                    "warning_message": "Пропущено КТГ!",
                    "action_message": "Сделайте КТГ при первой возможности"
                })
            if current_week >= 35:
                events.append({
                    "title": "Мазок на стрептококк группы В",
                    "event_type": Eventyp.analiz.value,
                    "week_of_pregnancy": 36,
                    "deadline_week": 37,
                    "is_critical": True,
                    "description": "Важный анализ перед родами",
                    "warning_message": "Пропущен мазок на стрептококк!",
                    "action_message": "Если не успели сдать до родов - обязательно скажите врачам в роддоме"
                })
            if current_week >= 36:
                events.append({
                    "title": "Повторные анализы (ВИЧ, гепатиты, сифилис, мазок, биохимия)",
                    "event_type": Eventyp.analiz.value,
                    "week_of_pregnancy": 36,
                    "deadline_week": 37,
                    "is_critical": True,
                    "description": "Контрольные анализы перед родами",
                    "warning_message": "Пропущены контрольные анализы!",
                    "action_message": "Срочно сдайте анализы"
                })
            if current_week >= 36:
                events.append({
                    "title": "Еженедельный визит к акушеру-гинекологу",
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": current_week,
                    "deadline_week": current_week + 1,
                    "is_critical": False,
                    "description": "Посещать врача каждую неделю",
                    "warning_message": "Пропущен еженедельный визит к врачу!",
                    "action_message": "Срочно запишитесь к врачу. Важно смотреть давление и отеки (риск преэклампсии)"
                })
        return events
    @staticmethod
    def generate_additional_events(user, current_week):
        """Генерация дополнительных событий на основе проблем со здоровьем"""
        events = []
        conditions = user.get_health_conditions_list()
        for condition in conditions:
            if condition in listdoctors:
                info = listdoctors[condition]
                events.append({
                    "title": f"Прием {info['doctor']} ({condition})",
                    "event_type": Eventyp.visit.value,
                    "week_of_pregnancy": info["week"],
                    "deadline_week": info["week"] + 4,
                    "is_critical": True,
                    "description": f"Осмотр {info['doctor']}. Частота: {info['frequency']}. Показание: {condition}",
                    "warning_message": f"Пропущен визит к {info['doctor']}!",
                    "action_message": "Срочно запишитесь к врачу"
                })
        if user.needs_perinatologist and conditions:
            events.append({
                "title": "Консультация перинатолога",
                "event_type": Eventyp.visit.value,
                "week_of_pregnancy": 12,
                "deadline_week": 20,
                "is_critical": True,
                "description": "Направление к врачу-перинатологу при серьезных проблемах со здоровьем",
                "warning_message": "У вас серьезные проблемы со здоровьем!",
                "action_message": "Не нашли своего врача? Получите направление к перинатологу"
            })
        return events
    @staticmethod
    def generate_for_user(user):
        """Полная генерация событий для пользователя"""
        current_week = user.calculate_current_week()
        events = []
        events.extend(Eventgenerator.generate_standard_events(user, current_week))
        if user.has_health_issues:
            events.extend(Eventgenerator.generate_additional_events(user, current_week))
        return events