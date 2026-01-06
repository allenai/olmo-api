from src.util.pii_regex import does_contain_pii


def test_does_contain_pii_matches_phone_numbers():
    tests = [
        (" 555-555-5555", True),
        ("555-555-5555", True),
        ("555-555-5555\n", True),
        ("(555)-555-5555", True),
        ("555.555.5555", True),
        ("55.555.5555", False),
    ]

    for input, expected in tests:
        assert does_contain_pii(input) == expected


def test_does_contain_pii_matches_email():
    tests = [
        ("fake@email.com", True),
        ("fake+stuff@email.com", True),
        ("fake.stuff@email.com", True),
        ("@", False),
        ("@home", False),
        ("home@", False),
    ]

    for input, expected in tests:
        assert does_contain_pii(input) == expected


def test_does_contain_pii_matches_ip_address():
    tests = [
        ("127.0.0.1", True),
        ("168.212.226.204", True),
        ("192.168.17.43", True),
        ("2001:db8:3:4::192.0.2.33", True),
        ("1:2:3:4:5:6::8", True),
        ("1.", False),
        ("1.2.3.", False),
        ("1: asdf\n2: asdf", False),
    ]

    for input, expected in tests:
        assert does_contain_pii(input) == expected
