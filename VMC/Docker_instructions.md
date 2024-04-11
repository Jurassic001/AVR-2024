<!--
First, [install Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
Then, run `pip install docker` if you haven't yet
-->

## Here's a bunch of Docker build commands
#### Note that images are mainly meant for the Jetson, although the root README offers instructions to build/run images not on a Jetson
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
<!--
<br/>

#### Or, if you want to setup all the containers at once, try this command:
(Note: This command will take approx. 30 mins to run. There's also a 90% chance that atleast one image will fail to setup properly (Won't interrupt the process). If the process is interrupted run `docker system prune` to delete any broken/half-downloaded images)
```
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