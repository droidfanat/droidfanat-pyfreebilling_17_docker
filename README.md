
# docker-Pyfreebilling

Run Pyfreebilling in a Docker container

## Usage

### Clone
   
    $ git clone https://github.com/droidfanat/droidfanat-pyfreebilling_17_docker.git ./pyfreebilling
    
### Build
    $cd ./pyfreebilling
    $ docker-compose build .
### Run
Foreground:
    $ docker-compose up -d

### Http 
     https://You ip
     Login:Admin
     Pass :Admin
### Setup env
    Uncoment 38 line docker-compose.yml
     - # network_mode: host
