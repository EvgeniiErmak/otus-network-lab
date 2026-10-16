#!/bin/bash
# Создание репозитория на GitHub (если его нет) и push через Personal access token (classic)
set -e
GH_USER="EvgeniiErmak"
REPO="otus-network-lab"
MSG="${1:-update}"

cd "$(dirname "$0")"

read -rsp "Введите Personal access token (classic): " TOKEN; echo

# Проверяем, существует ли репозиторий
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token ${TOKEN}" \
  https://api.github.com/repos/${GH_USER}/${REPO})

if [ "$CODE" = "404" ]; then
  echo ">>> Репозиторий не найден, создаю ${GH_USER}/${REPO}"
  curl -s -H "Authorization: token ${TOKEN}" -H "Accept: application/vnd.github+json" \
    -d "{\"name\":\"${REPO}\",\"description\":\"OTUS Linux Professional: сетевая лаборатория (Vagrant + Ansible)\",\"private\":false}" \
    https://api.github.com/user/repos | grep -E '"(full_name|html_url)"' | head -n 2
elif [ "$CODE" = "200" ]; then
  echo ">>> Репозиторий ${GH_USER}/${REPO} уже существует"
else
  echo "!!! Ошибка доступа к GitHub API (HTTP ${CODE}). Проверьте токен (нужен scope repo)."; exit 1
fi

git add -A
git commit -m "${MSG}" || echo ">>> Нет изменений для коммита"

# Push с токеном только в командной строке, в .git/config токен не сохраняется
git push "https://${GH_USER}:${TOKEN}@github.com/${GH_USER}/${REPO}.git" main
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GH_USER}/${REPO}.git"
git fetch origin 2>/dev/null || true
git branch --set-upstream-to=origin/main main 2>/dev/null || true
echo ">>> Готово: https://github.com/${GH_USER}/${REPO}"
