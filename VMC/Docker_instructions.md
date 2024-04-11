## Docker setup
- First, [install Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
- Then, run `pip install docker` if you haven't yet
- If you want to build/run Docker images **NOT** on a Jetson, run this command once first:

    ```bash
    docker run --rm --privileged docker.io/multiarch/qemu-user-static --reset -p yes
    ```

## Here's a bunch of Docker build commands

apriltag:
```bash
docker build -t apriltag ./VMC/apriltag/
```

fcm:
```bash
docker build -t fcm ./VMC/fcm/
```

fusion:
```bash
docker build -t fusion ./VMC/fusion/
```

mavp2p:
```bash
docker build -t mavp2p ./VMC/mavp2p/
```

mqtt:
```bash
docker build -t mqtt ./VMC/mqtt/
```

pcm:
```bash
docker build -t pcm ./VMC/pcm/
```

sandbox:
```bash
docker build -t sandbox ./VMC/sandbox/
```

simulator:
```bash
docker build -t simulator ./VMC/simulator/ # Broken
```

status:
```bash
docker build -t status ./VMC/status/
```

thermal:
```bash
docker build -t thermal ./VMC/thermal/
```

vio:
```bash
docker build -t vio ./VMC/vio/
```

## You'll also need to build the modules through start.py, since they're run through start.py
#### Note: If you update a VMC module you'll need to rebuild it
This command will build all modules:
```bash
start.py build
```
<!-- Ignore this section it's full of lies
<br/>

### Or, if you want to setup all the containers at once, try this command:
#### (Only recommended for first time setup)
(Note: This command will take approx. 30 mins to run. If the process is interrupted run `docker system prune` to delete any broken/half-downloaded images)
```bash
docker build -t apriltag ./VMC/apriltag/
docker build -t fcm ./VMC/fcm/
docker build -t fusion ./VMC/fusion/
docker build -t mavp2p ./VMC/mavp2p/
docker build -t mqtt ./VMC/mqtt/
docker build -t pcm ./VMC/pcm/
docker build -t sandbox ./VMC/sandbox/
docker build -t simulator ./VMC/simulator/
docker build -t status ./VMC/status/
docker build -t thermal ./VMC/thermal/
docker build -t vio ./VMC/vio/
```