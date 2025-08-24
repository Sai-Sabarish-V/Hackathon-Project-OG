from flask import Flask, render_template, redirect, request, url_for, jsonify, session, make_response
from datetime import datetime, timedelta
import json
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Store reservations in memory (in production, use a database)
seat_reservations = {}

# Floor configurations with charging sockets
FLOOR_CONFIG = {
    'ground': {
        'name': 'Ground Floor',
        'total_seats': 50,
        'charging_seats': list(random.sample(range(1, 51), 25))  # 25 seats with charging
    },
    'floor1': {
        'name': 'Floor 1',
        'total_seats': 100,
        'charging_seats': list(random.sample(range(1, 101), 50))  # 50 seats with charging
    },
    'floor2': {
        'name': 'Floor 2',
        'total_seats': 100,
        'charging_seats': list(random.sample(range(1, 101), 50))  # 50 seats with charging
    },
    'floor3': {
        'name': 'Floor 3',
        'total_seats': 100,
        'charging_seats': list(random.sample(range(1, 101), 50))  # 50 seats with charging
    }
}

@app.route('/')
@app.route('/home')
def home():
    user_info = session.get('user_info')
    return render_template('home.html', user_info=user_info)

@app.route('/about/<username>')
def about(username):
    return f'<h1>Hello, {username}!</h1>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        registration_number = request.form.get('registration_number')
        name = request.form.get('name')
        
        if registration_number and name:
            user_info = {
                'registration_number': registration_number,
                'name': name,
                'login_time': datetime.now().isoformat()
            }
            session['user_info'] = user_info
            
            response = make_response(redirect(url_for('home')))
            response.set_cookie('user_registration', registration_number, max_age=3600*24*7)
            response.set_cookie('user_name', name, max_age=3600*24*7)
            
            return response
        else:
            return render_template('login.html', error="Please fill in all fields")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_info', None)
    response = make_response(redirect(url_for('home')))
    response.delete_cookie('user_registration')
    response.delete_cookie('user_name')
    return response

@app.route('/seat-matrix')
def seat_matrix():
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('login'))
    return render_template('seat_matrix.html', reservations=seat_reservations, user_info=user_info, floor_config=FLOOR_CONFIG)

@app.route('/reserve-seat', methods=['POST'])
def reserve_seat():
    user_info = session.get('user_info')
    if not user_info:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    seat_number = data.get('seat_number')
    floor = data.get('floor')
    user_name = data.get('user_name')
    
    if seat_number and floor and user_name:
        # Check if user already has a reservation
        user_registration = user_info['registration_number']
        existing_reservation = None
        
        for seat_id, reservation in seat_reservations.items():
            if reservation['registration_number'] == user_registration:
                existing_reservation = seat_id
                break
        
        if existing_reservation:
            return jsonify({
                'success': False, 
                'message': 'You already have a reservation. Please cancel your existing reservation first.',
                'existing_reservation': existing_reservation
            })
        
        # Check if seat is already reserved
        seat_id = f"{floor}_{seat_number}"
        if seat_id in seat_reservations:
            return jsonify({'success': False, 'message': 'Seat is already reserved'})
        
        # Reserve seat for 10 minutes
        reservation_time = datetime.now()
        expiry_time = reservation_time + timedelta(minutes=10)
        
        seat_reservations[seat_id] = {
            'user_name': user_name,
            'registration_number': user_registration,
            'floor': floor,
            'seat_number': seat_number,
            'reserved_at': reservation_time.isoformat(),
            'expires_at': expiry_time.isoformat()
        }
        
        return jsonify({
            'success': True, 
            'message': f'Seat {seat_number} on {FLOOR_CONFIG[floor]["name"]} reserved for {user_name}',
            'expires_at': expiry_time.isoformat()
        })
    
    return jsonify({'success': False, 'message': 'Invalid data'})

@app.route('/cancel-reservation', methods=['POST'])
def cancel_reservation():
    user_info = session.get('user_info')
    if not user_info:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    data = request.get_json()
    seat_id = data.get('seat_id')
    user_name = data.get('user_name')
    
    if seat_id in seat_reservations:
        reservation = seat_reservations[seat_id]
        if reservation['user_name'] == user_name and reservation['registration_number'] == user_info['registration_number']:
            del seat_reservations[seat_id]
            return jsonify({'success': True, 'message': f'Reservation cancelled for seat {reservation["seat_number"]}'})
    
    return jsonify({'success': False, 'message': 'Reservation not found or unauthorized'})

@app.route('/get-user-reservation')
def get_user_reservation():
    user_info = session.get('user_info')
    if not user_info:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    user_registration = user_info['registration_number']
    
    for seat_id, reservation in seat_reservations.items():
        if reservation['registration_number'] == user_registration:
            return jsonify({
                'success': True,
                'reservation': {
                    'seat_id': seat_id,
                    'floor': reservation['floor'],
                    'seat_number': reservation['seat_number'],
                    'expires_at': reservation['expires_at']
                }
            })
    
    return jsonify({'success': False, 'message': 'No reservation found'})

if __name__ == '__main__':
    app.run(debug=True)
