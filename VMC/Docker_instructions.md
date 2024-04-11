## Heres a quick, rough walkthrough on how to setup an image on Docker, so you can run containers.

### First, [install Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
### Then, run `pip install docker` if you haven't yet
#### Then, based on the image you want to setup, pick from the following commands I've laid out:

apriltag:
```
docker build -t apriltag ./VMC/apriltag/
```

fcm:
```
docker build -t fcm ./VMC/fcm/
```

fusion:
```
docker build -t fusion ./VMC/fusion/
```

mavp2p:
```
docker build -t mavp2p ./VMC/mavp2p/
```

mqtt:
```
docker build -t mqtt ./VMC/mqtt/
```

pcm:
```
docker build -t pcm ./VMC/pcm/
```

sandbox:
```
docker build -t sandbox ./VMC/sandbox/
```

simulator:
```
docker build -t simulator ./VMC/simulator/
```

status:
```
docker build -t status ./VMC/status/
```

thermal:
```
docker build -t thermal ./VMC/thermal/
```

vio:
```
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