# Docker Instructions
## Docker setup
- First, [install Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
- Then, run `pip install docker` if you haven't yet
- If you want to build/run Docker images **NOT** on a Jetson, run this command once first:

    ```bash
    docker run --rm --privileged docker.io/multiarch/qemu-user-static --reset -p yes
    ```
<br/>

<!--
## Docker build commands
start.py build handles these commands for you so ignore this section

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
docker build -t simulator ./VMC/simulator/
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

<br/>

### Or, if you want to setup all the containers at once, try this command:
These commands will take AT LEAST 45 mins to run.
Note that an image failing to build won't interupt other images
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
echo off
```

<br/>
-->
## Building and running containers

#### IMPORTANT: Add `--help` to the end of these commands to see command syntax & options/configs

### You'll need to build the modules through start.py before running them
```bash
start.py build
```

Note: If you update a VMC module you'll need to rebuild it

### Then run the modules you want
```bash
start.py run
```

### Finally open up docker desktop and take a look at your glorious new container
### You can also run `app.py` in the GUI folder and connect to your container

<!-- Might add some example commands here in the future idk
## examples

-->