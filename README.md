<p align="center">
  <img src="docs/images/icon.png" width="128" alt="Lucid Blocks NX — Dimasick-git">
</p>

<h1 align="center">Lucid Blocks — NX</h1>

<p align="center">Неофициальный порт Lucid Blocks для Nintendo Switch.<br>Адаптация — <a href="https://github.com/Dimasick-git">Dimasick-git</a>.</p>

<p align="center">
  <a href="https://github.com/Dimasick-git/LUCID-BLOCKS-NX/releases/tag/v0.1.0-nsp01">Тестовый NSP</a> ·
  <a href="docs/INSTALL_RU.md">Установка</a> ·
  <a href="CHANGELOG.md">Изменения</a> ·
  <a href="https://github.com/Dimasick-git/LUCID-BLOCKS-NX/issues">Сообщить о баге</a>
</p>

## NSP01

Цельный установщик для DBI: движок, игровые ресурсы и готовый кеш мешей внутри одного NSP. Игровой пакет сжат без потерь с **1,50 ГБ до 815 МБ**. Данные читаются блоками прямо из установленной игры; распаковка полного пакета на microSD при запуске не нужна.

- Облегчённая вода: анимация и цвет сохранены, чтение экрана и глубины для преломления убрано.
- Матовое освещение блоков и отключённые локальные тени.
- Дальность 32 блока для минимального профиля, ограниченная очередь генерации чанков.
- 321 готовый меш предметов; варианты с общей иконкой переиспользуют геометрию.
- Поддержка SaltyNX: FPS после показа кадра и лимит FPSLocker через движок.

**Это prerelease для проверки.** Полный NSP ещё требует запуска на Switch. В тяжёлых местах остаются просадки; стабильные 60 FPS не подтверждены. Текущий драйвер не поддерживает бинарный кеш шейдеров — неиспользуемые проходы теперь не компилируются заранее, пустые файлы кеша не записываются.

## Установка

Установи `LUCID_BLOCKS_NX_FULL_NSP01.nsp` через DBI и запускай с HOME. Этот NSP содержит игру; прежний маленький форвардер запускал файлы с карты.

Сохранения остаются в `/switch/lucid-blocks/LucidBlocksNX/`, журнал — в `/switch/lucid-blocks/boot.log`. При обновлении эту папку сохраняй. [Подробная инструкция](docs/INSTALL_RU.md).

## Разработка

Основа: Godot/Horizon, GLES Compatibility и статический gdblocks с double precision. В репозитории находятся патчи, загрузчик, инструменты сборки и документация. Игровой пакет, установщики, ключи и личные сохранения в Git не включаются.

[Сборка и проверки](docs/DEVELOPMENT_RU.md) · [Формат сжатия](docs/PACK_FORMAT.md) · [Авторы и сторонний код](Credits.md)

Оригинальная игра: [Lucid Blocks в Steam](https://store.steampowered.com/app/3495730/). Порт не является официальным выпуском авторов игры.
