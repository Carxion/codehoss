from dojo_checks import docker, sh


def test_latest_is_the_new_version():
    sh("docker rmi localhost:5000/hello-app:latest")
    docker("pull", "-q", "localhost:5000/hello-app:latest")
    assert docker("run", "--rm", "localhost:5000/hello-app:latest") == "hello-app 1.1"
