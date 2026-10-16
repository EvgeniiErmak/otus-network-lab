#!/usr/bin/env python3
"""Расчёт подсетей: узлы, broadcast, проверка ошибок разбиения, поиск свободных подсетей."""
import ipaddress as ip

NETS = [
    ("Central", "Directors",                     "192.168.0.0/28"),
    ("Central", "Office hardware",               "192.168.0.32/28"),
    ("Central", "Wifi (mgt network)",            "192.168.0.64/26"),
    ("Office1", "Dev",                           "192.168.2.0/26"),
    ("Office1", "Test servers",                  "192.168.2.64/26"),
    ("Office1", "Managers",                      "192.168.2.128/26"),
    ("Office1", "Office hardware",               "192.168.2.192/26"),
    ("Office2", "Dev",                           "192.168.1.0/25"),
    ("Office2", "Test servers",                  "192.168.1.128/26"),
    ("Office2", "Office hardware",               "192.168.1.192/26"),
    ("Links",   "inetRouter - centralRouter",    "192.168.255.0/30"),
    ("Links",   "centralRouter - office2Router", "192.168.255.4/30"),
    ("Links",   "centralRouter - office1Router", "192.168.255.8/30"),
]
SUPERNETS = ["192.168.0.0/24", "192.168.1.0/24", "192.168.2.0/24", "192.168.255.0/24"]

HDR = "| Group | Name | Network | Netmask | N (hosts) | HostMin | HostMax | Broadcast |\n|---|---|---|---|---|---|---|---|"

def row(group, name, n):
    return (f"| {group} | {name} | {n} | {n.netmask} | {n.num_addresses - 2} | "
            f"{n.network_address + 1} | {n.broadcast_address - 1} | {n.broadcast_address} |")

errors = 0
used = []
print("## 1. Проверка корректности разбиения\n")
for g, name, cidr in NETS:
    try:
        used.append((g, name, ip.ip_network(cidr, strict=True)))
    except ValueError as e:
        errors += 1
        print(f"- ОШИБКА: {cidr} ({name}) - адрес не совпадает с границей сети: {e}")

for i in range(len(used)):
    for j in range(i + 1, len(used)):
        a, b = used[i][2], used[j][2]
        if a.overlaps(b):
            errors += 1
            print(f"- ОШИБКА: пересечение {a} ({used[i][1]}) и {b} ({used[j][1]})")

print("- Ошибок при разбиении не найдено\n" if errors == 0 else f"\nНайдено ошибок: {errors}\n")

print("## 2. Занятые подсети\n")
print(HDR)
for g, name, n in used:
    print(row(g, name, n))

print("\n## 3. Свободные подсети\n")
print(HDR)
for s in SUPERNETS:
    free = [ip.ip_network(s)]
    for _, _, u in used:
        nxt = []
        for f in free:
            if u.subnet_of(f):
                nxt.extend(f.address_exclude(u))
            elif not f.subnet_of(u):
                nxt.append(f)
        free = nxt
    for f in sorted(ip.collapse_addresses(free)):
        print(row("Free", s, f))
