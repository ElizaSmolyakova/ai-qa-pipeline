import requests

def test_pay_example(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 100, 'currency': 'RUB'})
    assert response.status_code == 200

def test_pay_positive_small_amount(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 4999, 'currency': 'RUB'})
    assert response.status_code == 200

def test_pay_positive_large_amount(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 5001, 'currency': 'RUB'})
    assert response.status_code == 202

def test_pay_negative_amount(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': -100, 'currency': 'RUB'})
    assert response.status_code == 400

def test_pay_zero_amount(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 0, 'currency': 'RUB'})
    assert response.status_code == 400

def test_pay_invalid_currency(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 100, 'currency': 'USD'})
    assert response.status_code == 422

def test_pay_positive_small_amount_rub(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 4999, 'currency': 'RUB'})
    assert response.status_code == 200

def test_pay_positive_large_amount_rub(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 5001, 'currency': 'RUB'})
    assert response.status_code == 202

def test_pay_negative_amount_rub(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': -100, 'currency': 'RUB'})
    assert response.status_code == 400

def test_pay_zero_amount_rub(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 0, 'currency': 'RUB'})
    assert response.status_code == 400

def test_pay_invalid_currency_rub(base_url):
    response = requests.post(f'{base_url}/api/v1/pay', json={'amount': 100, 'currency': 'USD'})
    assert response.status_code == 422