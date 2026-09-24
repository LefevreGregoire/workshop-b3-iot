# Inter-Vessel Security Center (IoT)

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/MQTT-Mosquitto-3C5280?style=flat-square&logo=eclipse-mosquitto" alt="MQTT">
  <img src="https://img.shields.io/badge/Flask-Web_Dashboard-000000?style=flat-square&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-Persistence-003B57?style=flat-square&logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/Cryptography-AES--128-red?style=flat-square" alt="AES-128">
</p>

## À propos du projet

Ce dépôt documente la mise en place d'une architecture IoT sécurisée pour un réseau de capteurs embarqués. 
Le système repose sur une communication MQTT chiffrée, protégée par mot de passe, et supervisée par un **Système de Détection d'Intrusion (IDS)** automatique capable de détecter, journaliser et bloquer les tentatives de piratage.

## Architecture & Sécurité

Le réseau est composé d'un **Serveur Central** (Dashboard Web + IDS + Broker MQTT) et de multiples **Capteurs** (ex: digicode, détecteur de mouvement, terminaux de chat). 

Pour garantir une sécurité maximale face aux attaques, les mécanismes suivants ont été déployés :

* **Authentification Stricte :** Le broker Mosquitto n'accepte aucune connexion anonyme. Tous les devices utilisent des identifiants (fichiers `passwd` chiffrés).
* **Chiffrement AES-128 Fernet :** L'intégralité des payloads MQTT est chiffrée de bout-en-bout. L'IDS bloque instantanément tout message en clair (Alerte `UNENCRYPTED_PAYLOAD`).
* **Protection Anti-Replay :** Chaque message chiffré inclut un Token horodaté (TTL de 300s). L'IDS rejette systématiquement les vieux tokens interceptés et rejoués (Alerte `INVALID_TOKEN`).
* **Isolation Automatique (Watchdog) :** Si un appareil se comporte de manière malveillante (brute-force, spam de requêtes invalides), le serveur le place en quarantaine (`ISOLATED`).

## Fonctionnalités Principales

* 🌐 **Dashboard Web Temps Réel** : Interface graphique permettant de visualiser l'état des appareils, la consommation CPU/RAM, et les logs d'incidents (accessible via `http://[IP]:5000`).
* 💬 **Secure Chat Terminal** : Application de messagerie inter-vaisseaux chiffrée de bout-en-bout via MQTT (`py/chat.py`).
* 🏴‍☠️ **Simulateur d'Attaques** : Un script de test (`test_hacker.py`) est fourni pour démontrer l'efficacité de l'IDS face à des attaques par injection en clair ou par rejeu de tokens.

## Prérequis et Installation

1. Installer les dépendances système et Python :
   ```bash
   sudo apt-get install python3-dev gcc mosquitto-clients
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Démarrer le Broker MQTT sécurisé avec Docker :
   ```bash
   cd docker
   docker compose up -d
   ```
3. Lancer le Serveur Central (IDS & Web) :
   ```bash
   cd py
   python3 server.py
   ```
4. Démarrer un capteur sur une autre carte :
   ```bash
   python3 py/digicode.py
   ```
