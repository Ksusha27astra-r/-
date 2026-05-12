from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta, date
from models import db, Userprofile, Pregnancyevent, Eventgenerator, listdoctors
import json
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pregnancy_calendar.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'
db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()
        # Создаем тестового пользователя
        if not Userprofile.query.first():
            conception_date = date.today() - timedelta(days=70)
            user = Userprofile(
                conception_date=conception_date,
                has_health_issues=False,
                health_conditions='[]',
                needs_perinatologist=False,
                joined_week=10
            )
            db.session.add(user)
            db.session.commit()
            events = Eventgenerator.generate_for_user(user)
            for event_data in events:
                days_from_conception = event_data['week_of_pregnancy'] * 7
                scheduled_date = conception_date + timedelta(days=days_from_conception)
                event = Pregnancyevent(
                    user_id=user.id,
                    title=event_data['title'],
                    event_type=event_data['event_type'],
                    week_of_pregnancy=event_data['week_of_pregnancy'],
                    scheduled_date=scheduled_date,
                    deadline_week=event_data.get('deadline_week'),
                    description=event_data.get('description', ''),
                    is_critical=event_data.get('is_critical', False),
                    warning_message=event_data.get('warning_message'),
                    action_message=event_data.get('action_message')
                )
                db.session.add(event)
            db.session.commit()
            print(f"Создан пользователь с {len(events)} событиями")
@app.route('/')
def index():
    return render_template('calendar.html')

@app.route('/api/user/profile')
def get_user_profile():
    """Получить профиль пользователя"""
    user = Userprofile.query.first()
    if user:
        current_week = user.calculate_current_week()
        due_date = user.conception_date + timedelta(days=280)
        days_left = (due_date - date.today()).days
        return jsonify({
            'id': user.id,
            'current_week': current_week,
            'conception_date': user.conception_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'days_left': max(0, days_left),
            'trimester': 1 if current_week <= 13 else (2 if current_week <= 27 else 3),
            'has_health_issues': user.has_health_issues,
            'health_conditions': user.get_health_conditions_list(),
            'needs_perinatologist': user.needs_perinatologist,
            'joined_week': user.joined_week
        })
    return jsonify({'error': 'User not found'}), 404
@app.route('/api/events')
def get_events():
    """Получить все события с актуальными статусами"""
    user = Userprofile.query.first()
    if not user:
        return jsonify({'events': []})
    current_week = user.calculate_current_week()
    events = Pregnancyevent.query.filter_by(user_id=user.id).order_by(Pregnancyevent.week_of_pregnancy).all()
    events_by_week = {}
    for event in events:
        week = event.week_of_pregnancy
        if week not in events_by_week:
            events_by_week[week] = []
        events_by_week[week].append(event.to_dict(current_week))
    return jsonify({
        'events_by_week': events_by_week,
        'current_week': current_week
    })
@app.route('/api/events/<int:event_id>', methods=['PUT'])
def complete_event(event_id):
    """Отметить событие выполненным"""
    event = Pregnancyevent.query.get_or_404(event_id)
    event.is_completed = True
    db.session.commit()
    return jsonify({'success': True})
@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Удалить событие"""
    event = Pregnancyevent.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'success': True})
@app.route('/api/health-issues')
def get_health_issues():
    """Получить список всех возможных проблем со здоровьем"""
    issues = Eventgenerator.get_all_available_health_issues()
    return jsonify({'issues': issues})

@app.route('/api/user/health', methods=['POST'])
def update_user_health():
    """Обновить информацию о здоровье пользователя"""
    data = request.json
    user = Userprofile.query.first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    has_issues = data.get('has_issues', False)
    conditions = data.get('conditions', [])
    user.has_health_issues = has_issues
    user.set_health_conditions(conditions)
    user.needs_perinatologist = has_issues
    db.session.commit()
    Pregnancyevent.query.filter_by(user_id=user.id, is_completed=False).delete()
    events = Eventgenerator.generate_for_user(user)
    for event_data in events:
        days_from_conception = event_data['week_of_pregnancy'] * 7
        scheduled_date = user.conception_date + timedelta(days=days_from_conception)
        event = Pregnancyevent(
            user_id=user.id,
            title=event_data['title'],
            event_type=event_data['event_type'],
            week_of_pregnancy=event_data['week_of_pregnancy'],
            scheduled_date=scheduled_date,
            deadline_week=event_data.get('deadline_week'),
            description=event_data.get('description', ''),
            is_critical=event_data.get('is_critical', False),
            warning_message=event_data.get('warning_message'),
            action_message=event_data.get('action_message')
        )
        db.session.add(event)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Создано {len(events)} событий'})
@app.route('/api/critical-warnings')
def get_critical_warnings():
    """Получить критические предупреждения для пользователя"""
    user = Userprofile.query.first()
    if not user:
        return jsonify({'warnings': []})
    current_week = user.calculate_current_week()
    events = Pregnancyevent.query.filter_by(
        user_id=user.id,
        is_completed=False,
        is_critical=True
    ).all()
    warnings = []
    for event in events:
        if event.get_status(current_week) == 'просрочено':
            warnings.append({
                'title': event.title,
                'week': event.week_of_pregnancy,
                'warning_message': event.warning_message,
                'action_message': event.action_message
            })
    return jsonify({'warnings': warnings})
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)