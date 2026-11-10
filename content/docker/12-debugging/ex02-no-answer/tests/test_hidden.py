from dojo_checks import lab_file


def test_listens_on_all_interfaces():
    assert "127.0.0.1" not in lab_file("server.py"), "server.py still listens on 127.0.0.1"
