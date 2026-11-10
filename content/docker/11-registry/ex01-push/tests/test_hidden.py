from dojo_checks import docker


def test_pull_back_and_run():
    docker("rmi", "localhost:5000/hello-app:1.0")
    docker("pull", "-q", "localhost:5000/hello-app:1.0")
    assert docker("run", "--rm", "localhost:5000/hello-app:1.0") == "hello-app 1.0"
