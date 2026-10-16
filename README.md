# Сетевая лаборатория: Vagrant + Ansible

Домашнее задание курса OTUS «Администратор Linux. Professional» — «Разворачиваем сетевую лабораторию».

| Раздел репозитория | Содержимое |
|---|---|
| [Vagrantfile](Vagrantfile) | 7 ВМ Ubuntu 22.04, сети и запуск Ansible |
| [ansible/](ansible/) | inventory [hosts](ansible/hosts) и playbook [provision.yml](ansible/provision.yml) |
| [ansible/templates/](ansible/templates/) | netplan-конфиги хостов, правила NAT, настройки DNS |
| [theory/](theory/) | расчёт подсетей: [subnets.md](theory/subnets.md), [ipcalc.txt](theory/ipcalc.txt), [check_subnets.py](theory/check_subnets.py) |
| [tests/](tests/) | проверка связности и traceroute |
| [screenshots/](screenshots/) | скриншоты выполнения |
| [git_push.sh](git_push.sh) | создание репозитория и push через Personal access token |

## Задание

Построить сеть из трёх площадок (Central, Office1, Office2) с выходом в интернет через inetRouter:

- **Office1:** `192.168.2.0/26` dev, `192.168.2.64/26` test servers, `192.168.2.128/26` managers, `192.168.2.192/26` office hardware.
- **Office2:** `192.168.1.0/25` dev, `192.168.1.128/26` test servers, `192.168.1.192/26` office hardware.
- **Central:** `192.168.0.0/28` directors, `192.168.0.32/28` office hardware, `192.168.0.64/26` wifi.

Серверы: inetRouter, centralRouter, office1Router, office2Router, centralServer, office1Server, office2Server.

**Теория:** найти свободные подсети, посчитать количество узлов в каждой подсети, указать broadcast-адреса, проверить разбиение на ошибки.

**Практика:**
- соединить офисы и настроить маршрутизацию;
- весь интернет-трафик пускать через inetRouter;
- все серверы должны видеть друг друга;
- отключить маршрут по умолчанию на `eth0` (NAT Vagrant) у новых серверов;
- формат сдачи: Vagrant + Ansible.

## Схема сети

~~mermaid
flowchart TB
  NET((Internet)) --- IR["inetRouter<br/>eth0: NAT VirtualBox<br/>eth1: 192.168.255.1/30"]
  IR ---|"192.168.255.0/30"| CR["centralRouter<br/>255.2 · 0.1 · 0.33 · 0.65 · 255.9 · 255.5"]
  CR ---|"directors 192.168.0.0/28"| CS["centralServer<br/>192.168.0.2/28"]
  CR -.- CN["office hardware 192.168.0.32/28<br/>wifi 192.168.0.64/26"]
  CR ---|"192.168.255.8/30"| O1R["office1Router<br/>255.10 · 2.1 · 2.65 · 2.129 · 2.193"]
  CR ---|"192.168.255.4/30"| O2R["office2Router<br/>255.6 · 1.1 · 1.129 · 1.193"]
  O1R ---|"managers 192.168.2.128/26"| O1S["office1Server<br/>192.168.2.130/26"]
  O1R -.- O1N["dev 192.168.2.0/26<br/>test 192.168.2.64/26<br/>hardware 192.168.2.192/26"]
  O2R ---|"dev 192.168.1.0/25"| O2S["office2Server<br/>192.168.1.2/25"]
  O2R -.- O2N["test 192.168.1.128/26<br/>hardware 192.168.1.192/26"]
~~

Кроме того, у всех ВМ есть адрес в сети управления `192.168.50.0/24`, через которую работает Ansible.

### Адреса и маршруты

| Хост | Интерфейсы | Статические маршруты |
|---|---|---|
| inetRouter | eth0 NAT (DHCP), eth1 `192.168.255.1/30`, eth2 `192.168.50.10` | default через eth0 (NAT), `192.168.0.0/16` → `192.168.255.2` |
| centralRouter | eth1 `192.168.255.2/30`, eth2 `192.168.0.1/28`, eth3 `192.168.0.33/28`, eth4 `192.168.0.65/26`, eth5 `192.168.255.9/30`, eth6 `192.168.255.5/30`, eth7 `192.168.50.11` | default → `192.168.255.1`, `192.168.2.0/24` → `192.168.255.10`, `192.168.1.0/24` → `192.168.255.6` |
| centralServer | eth1 `192.168.0.2/28`, eth2 `192.168.50.12` | default → `192.168.0.1` |
| office1Router | eth1 `192.168.255.10/30`, eth2 `192.168.2.1/26`, eth3 `192.168.2.65/26`, eth4 `192.168.2.129/26`, eth5 `192.168.2.193/26`, eth6 `192.168.50.20` | default → `192.168.255.9` |
| office1Server | eth1 `192.168.2.130/26`, eth2 `192.168.50.21` | default → `192.168.2.129` |
| office2Router | eth1 `192.168.255.6/30`, eth2 `192.168.1.1/25`, eth3 `192.168.1.129/26`, eth4 `192.168.1.193/26`, eth5 `192.168.50.30` | default → `192.168.255.5` |
| office2Server | eth1 `192.168.1.2/25`, eth2 `192.168.50.31` | default → `192.168.1.1` |

## Теоретическая часть

Расчёт выполнен скриптом [theory/check_subnets.py](theory/check_subnets.py) (модуль `ipaddress`) и сверен с `ipcalc` ([theory/ipcalc.txt](theory/ipcalc.txt)).

**Проверка разбиения:** все сети выровнены по границе маски, пересечений нет. Ошибок не найдено.

### Занятые подсети

| Площадка | Назначение | Сеть | Маска | Узлов | HostMin | HostMax | Broadcast |
|---|---|---|---|---|---|---|---|
| Central | Directors | 192.168.0.0/28 | 255.255.255.240 | 14 | 192.168.0.1 | 192.168.0.14 | 192.168.0.15 |
| Central | Office hardware | 192.168.0.32/28 | 255.255.255.240 | 14 | 192.168.0.33 | 192.168.0.46 | 192.168.0.47 |
| Central | Wifi (mgt) | 192.168.0.64/26 | 255.255.255.192 | 62 | 192.168.0.65 | 192.168.0.126 | 192.168.0.127 |
| Office1 | Dev | 192.168.2.0/26 | 255.255.255.192 | 62 | 192.168.2.1 | 192.168.2.62 | 192.168.2.63 |
| Office1 | Test servers | 192.168.2.64/26 | 255.255.255.192 | 62 | 192.168.2.65 | 192.168.2.126 | 192.168.2.127 |
| Office1 | Managers | 192.168.2.128/26 | 255.255.255.192 | 62 | 192.168.2.129 | 192.168.2.190 | 192.168.2.191 |
| Office1 | Office hardware | 192.168.2.192/26 | 255.255.255.192 | 62 | 192.168.2.193 | 192.168.2.254 | 192.168.2.255 |
| Office2 | Dev | 192.168.1.0/25 | 255.255.255.128 | 126 | 192.168.1.1 | 192.168.1.126 | 192.168.1.127 |
| Office2 | Test servers | 192.168.1.128/26 | 255.255.255.192 | 62 | 192.168.1.129 | 192.168.1.190 | 192.168.1.191 |
| Office2 | Office hardware | 192.168.1.192/26 | 255.255.255.192 | 62 | 192.168.1.193 | 192.168.1.254 | 192.168.1.255 |
| Линк | inetRouter — centralRouter | 192.168.255.0/30 | 255.255.255.252 | 2 | 192.168.255.1 | 192.168.255.2 | 192.168.255.3 |
| Линк | centralRouter — office2Router | 192.168.255.4/30 | 255.255.255.252 | 2 | 192.168.255.5 | 192.168.255.6 | 192.168.255.7 |
| Линк | centralRouter — office1Router | 192.168.255.8/30 | 255.255.255.252 | 2 | 192.168.255.9 | 192.168.255.10 | 192.168.255.11 |

### Свободные подсети

| Сеть | Маска | Узлов | HostMin | HostMax | Broadcast |
|---|---|---|---|---|---|
| 192.168.0.16/28 | 255.255.255.240 | 14 | 192.168.0.17 | 192.168.0.30 | 192.168.0.31 |
| 192.168.0.48/28 | 255.255.255.240 | 14 | 192.168.0.49 | 192.168.0.62 | 192.168.0.63 |
| 192.168.0.128/25 | 255.255.255.128 | 126 | 192.168.0.129 | 192.168.0.254 | 192.168.0.255 |
| 192.168.255.12/30 | 255.255.255.252 | 2 | 192.168.255.13 | 192.168.255.14 | 192.168.255.15 |
| 192.168.255.16/28 | 255.255.255.240 | 14 | 192.168.255.17 | 192.168.255.30 | 192.168.255.31 |
| 192.168.255.32/27 | 255.255.255.224 | 30 | 192.168.255.33 | 192.168.255.62 | 192.168.255.63 |
| 192.168.255.64/26 | 255.255.255.192 | 62 | 192.168.255.65 | 192.168.255.126 | 192.168.255.127 |
| 192.168.255.128/25 | 255.255.255.128 | 126 | 192.168.255.129 | 192.168.255.254 | 192.168.255.255 |

Сети `192.168.1.0/24` (Office2) и `192.168.2.0/24` (Office1) заняты полностью.

## Развёртывание

Хост: Ubuntu 26.04, VirtualBox 7.2.6, Vagrant 2.4.9, ansible-core 2.20.1.

~~bash
# VirtualBox 7 разрешает host-only сети только из 192.168.56.0/21 - добавляем сеть управления
echo "* 192.168.50.0/24 192.168.56.0/21" > /etc/vbox/networks.conf

git clone https://github.com/EvgeniiErmak/otus-network-lab.git
cd otus-network-lab
vagrant up          # создаёт 7 ВМ, после последней (office2Server) запускается Ansible
~~

Повторный запуск настройки: `vagrant provision` или `ansible-playbook ansible/provision.yml`.

### Что делает [playbook](ansible/provision.yml)

1. **inetRouter:** отключает ufw, ставит правила NAT (`MASQUERADE ! -d 192.168.0.0/16 -o eth0`) из [iptables_rules.ipv4](ansible/templates/iptables_rules.ipv4) и настраивает их восстановление при загрузке.
2. **Роутеры:** включает `net.ipv4.conf.all.forwarding = 1`.
3. **Все хосты:** настраивает DNS в systemd-resolved ([resolved-lab.conf](ansible/templates/resolved-lab.conf)).
4. **Все, кроме inetRouter:** отключает маршрут по умолчанию на `eth0` ([00-installer-config.yaml](ansible/templates/00-installer-config.yaml)).
5. **Все хосты:** раскладывает адреса и статические маршруты, шаблон `50-vagrant_<хост>.yaml` для каждого хоста.
6. Перезагружает все хосты и ставит `traceroute`. `apt` при этом уже ходит в интернет через inetRouter, так что установка сама служит проверкой.

## Проверка

**Все серверы видят друг друга.** Скрипт [tests/ping_matrix.sh](tests/ping_matrix.sh) запускает ping с каждого хоста до каждого (результат в [ping_matrix.txt](tests/ping_matrix.txt)):

~~
$ ./tests/ping_matrix.sh > /tmp/pm.txt; echo "OK: $(grep -c OK /tmp/pm.txt)  FAIL: $(grep -c FAIL /tmp/pm.txt)"
OK: 49  FAIL: 0
~~

**Интернет идёт через inetRouter** ([traceroute_internet.txt](tests/traceroute_internet.txt)):

~~
office1Server$ traceroute -n -m 4 8.8.8.8
 1  192.168.2.129    # office1Router
 2  192.168.255.9    # centralRouter
 3  192.168.255.1    # inetRouter
 4  10.0.2.2         # NAT VirtualBox
~~

**На серверах нет маршрута по умолчанию через eth0:**

~~
office1Server$ ip r
default via 192.168.2.129 dev eth1 proto static
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100
192.168.2.128/26 dev eth1 proto kernel scope link src 192.168.2.130
192.168.50.0/24 dev eth2 proto kernel scope link src 192.168.50.21
~~

Путь между офисами: [traceroute_office1_office2.txt](tests/traceroute_office1_office2.txt). После перезагрузки всех хостов NAT, маршруты и связность сохраняются (49/49).

## Особенности реализации

- **Офисы и линки.** Офисы подключены к centralRouter отдельными сетями `/30`: `192.168.255.8/30` (office1) и `192.168.255.4/30` (office2). На центральном роутере обратные маршруты агрегированы до `/24` на офис, на inetRouter — до `192.168.0.0/16`.
- **Два конфига eth0.** В box `generic/ubuntu2204` интерфейс `eth0` описан в двух netplan-файлах (`00-installer-config.yaml` и `01-netcfg.yaml`), поэтому маршрут по умолчанию отключается в обоих. Отключены также RA (`accept-ra: false`), иначе через NAT VirtualBox работал бы IPv6 в обход inetRouter.
- **DNS.** В box включена строгая проверка DNSSEC (`missing-key`), из-за которой не разрешались имена. Отключена через drop-in systemd-resolved. DNS-серверы заданы глобально, а не на `eth0`: resolved шлёт запросы к DNS интерфейса только через этот интерфейс, а маршрута по умолчанию на `eth0` нет.
- **Сохранение NAT.** Скрипт `/etc/network/if-pre-up.d/iptables` из методички срабатывает только с ifupdown, а в Ubuntu 22.04 сетью управляет systemd-networkd. Поэтому правила восстанавливает systemd-юнит [iptables-restore.service](ansible/templates/iptables-restore.service).
- **Forwarding.** Включается файлом в `/etc/sysctl.d/`, внешние коллекции Ansible не нужны.
- **Неточности в методичке.**
  - В списке свободных сетей указаны `192.168.255.4/30` и `192.168.255.8/29`, хотя они заняты линками к офисам, и пропущена `192.168.255.128/25`.
  - У office2 в таблице адресов указана маска `/26`, а сеть dev2 — `/25` (в Vagrantfile маска верная).
- **`vagrant reload`.** При `vagrant reload` или `vagrant halt` с последующим `vagrant up` Vagrant перезаписывает `/etc/netplan/50-vagrant.yaml`, и маршруты пропадают, поэтому после этих команд нужен `vagrant provision`. Обычная перезагрузка ВМ настройки сохраняет.
