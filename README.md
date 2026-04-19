# PubChat Smart Literature Search Project User Guide

## 🇬🇧 English Version

### 1. Prerequisites
1. Please use a VPN if your region or country has network limitations, otherwise Docker image pulling will fail.

2. Please ensure **Docker**  https://www.docker.com   is installed and running on your local machine (start Docker Desktop for Win / macOS then continue following steps).

### 2. Quick Start Steps
1.  **Mac/Linux User**
    Open ‘Terminal’, copy the command below and press ’Enter‘：
```bash
    curl -L -o PubChat.zip https://github.com/PubChatOfficial/PubChat_smart_literature_search/archive/refs/heads/main.zip && unzip -q PubChat.zip && cd PubChat_smart_literature_search-main && docker compose up -d && rm ../PubChat.zip
```

2.  **Windows User**
    Press the ’Win‘ key, search for ’PowerShell‘, open it, then copy the command below and press ’Enter‘：
```bash
    Invoke-WebRequest -Uri "https://github.com/PubChatOfficial/PubChat_smart_literature_search/archive/refs/heads/main.zip" -OutFile "PubChat.zip"; Expand-Archive -Path "PubChat.zip" -DestinationPath "."; cd PubChat_smart_literature_search-main; docker compose up -d; Remove-Item "..\PubChat.zip"
 ```
    

### 4. Access the Application
Once the services are ready, open your browser and visit:   
    http://localhost:8000

### 4. Stop the Services
To shut down the project, run this command in the project root directory. Containers will shut down automatically:
```bash
    docker compose down
```


---


# PubChat 智能文献检索项目使用指南


## 🇨🇳 中文版

### 一、环境准备
1. 如果所处国家或地区存在网络封锁或异常，请自行开启VPN，否则会出现镜像拉取失败等问题。

2. 请确保本地已安装 **Docker**  https://www.docker.com  ， 并且 Docker 服务处于**正常运行状态**（Win / macOS 用户启动 Docker Desktop 再进行后续操作）。

### 二、快速启动步骤
1.  **Mac/Linux用户**
    打开**“终端 (Terminal)”，复制粘贴这一整行**代码并回车：
```bash
    curl -L -o PubChat.zip https://github.com/PubChatOfficial/PubChat_smart_literature_search/archive/refs/heads/main.zip && unzip -q PubChat.zip && cd PubChat_smart_literature_search-main && docker compose up -d && rm ../PubChat.zip
```

2.  **Win用户**
    按 Win键，搜索 PowerShell并打开，然后复制粘贴这一整行代码并回车：
```bash
    Invoke-WebRequest -Uri "https://github.com/PubChatOfficial/PubChat_smart_literature_search/archive/refs/heads/main.zip" -OutFile "PubChat.zip"; Expand-Archive -Path "PubChat.zip" -DestinationPath "."; cd PubChat_smart_literature_search-main; docker compose up -d; Remove-Item "..\PubChat.zip"
 ```

### 三、访问应用
服务启动成功后，打开浏览器，访问以下地址：
    http://localhost:8000

### 四、停止服务
如需关闭项目，在项目根目录执行，容器会自动关闭退出：
```bash
    docker compose down
```
      
