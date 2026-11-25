import requests


def test_pos_pay_default_rub(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 200


def test_pos_pay_default_rub_5000(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 200


def test_pos_pay_default_rub_5001(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 202


def test_pos_pay_default_rub_10000(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 202


def test_pos_pay_default_rub_15000(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 202


def test_pos_pay_default_rub_15001(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 202


def test_neg_pay_default_rub_negative(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 400


def test_neg_pay_default_rub_zero(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 400


def test_pos_pay_default_usd(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 200


def test_neg_pay_default_non_supported(base_url):
    response = requests.get(f'{base_url}/api/v1/pay')
    assert response.status_code == 422