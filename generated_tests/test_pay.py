import requests

def test_pay_positive(base_url):
    endpoint = '/api/v1/pay'
    payload = {'amount': 5001, 'currency': 'USD'}
    response = requests.post(f'{base_url}{endpoint}', json=payload)
    assert response.status_code == 422

def test_pay_negative_zero_amount(base_url):
    endpoint = '/api/v1/pay'
    payload = {'amount': 0, 'currency': 'USD'}
    response = requests.post(f'{base_url}{endpoint}', json=payload)
    assert response.status_code == 400

def test_pay_negative_negative_amount(base_url):
    endpoint = '/api/v1/pay'
    payload = {'amount': -100, 'currency': 'USD'}
    response = requests.post(f'{base_url}{endpoint}', json=payload)
    assert response.status_code == 400

def test_pay_correct_currency(base_url):
    endpoint = '/api/v1/pay'
    payload = {'amount': 5000, 'currency': 'USD'}
    response = requests.post(f'{base_url}{endpoint}', json=payload)
    assert response.status_code == 422

def test_pay_negative_invalid_currency(base_url):
    endpoint = '/api/v1/pay'
    payload = {'amount': 5000, 'currency': 'XYZ'}
    response = requests.post(f'{base_url}{endpoint}', json=payload)
    assert response.status_code == 422
