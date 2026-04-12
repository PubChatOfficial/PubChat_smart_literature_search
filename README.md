# PubChat Search Project User Guide

---

## 🇬🇧 English Version

### 1. Prerequisites
Please ensure **Docker** https://www.docker.com  is installed and running on your local machine (start Docker Desktop for Windows / macOS users).

### 2. Quick Start Steps
1.  **Get the Project**
    Clone the project repository to your local machine, or download and extract the project ZIP file.

2.  **Start the Services**
    Open a terminal, navigate to the project root directory, and run the following command to start all services:
    ```bash
    docker compose up -d 
    ```
    Wait for the images to be pulled, containers to be built, and services to start.

3.  **Access the Application**
    Once the services are ready, open your browser and visit:   
    http://localhost:8000

### 3. Stop the Services
To shut down the project, run this command in the project root directory:
    ```bash
    docker compose down
    ```
    Containers will shut down automatically.


---


# PubChat Search 项目使用指南


## 🇨🇳 中文版

### 一、环境准备s
请确保本地已安装 **Docker** https://www.docker.com ， 并且 Docker 服务处于**正常运行状态**（Windows / macOS 用户启动 Docker Desktop 即可）。

### 二、快速启动步骤
1.  **拉取项目资源**
    将项目代码克隆到本地，或下载项目压缩包并解压。

2.  **启动项目服务**
    打开终端，进入项目根目录，执行以下命令启动所有服务：
    ```bash
    docker compose up -d
    ```
    等待镜像拉取、容器构建和服务启动完成。

3.  **访问应用**
    服务启动成功后，打开浏览器，访问以下地址：
    http://localhost:8000

### 三、停止服务
如需关闭项目，在项目根目录执行：
    ```bash
    docker compose down
    ```
    容器会自动关闭退出。
      