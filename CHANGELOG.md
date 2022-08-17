# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0.html)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## master
  [11.0b11]

## testing
  [12.0.0-beta]

## [14.0.0-beta] - 2022/08/04
- [added] upgrade base system to Debian 11
- [added] build ISO file script
- [added] Makefile  
- [changed] snapshot folder path
- [changed] configuration folder path

## [12.1.1-beta] - 2021/11/06
- [removed] encode snapshot feature with JWT
- [changed] snapshot folder path to /home/user/wb/snapshots/
- [changed] configuration folder path /home/user/wb/settings/

## [12.1.0-beta] - 2021/11/05
- [added] add datetime (hh:mm:ss) on snapshot filename
- [changed] snapshot folder path
- [changed] configuration folder path
- [fixed] erase settings variables
- [fixed] token on submit function
- [fixed] requirement pyjwt version on Debian 9

## [12.0.0-beta] - 2021/05/25
- [added] first version with decoupled configuration

## [11.1.0-beta]
- [added] adding new settings.ini file
- [added] adding config.py file with python-decouple
