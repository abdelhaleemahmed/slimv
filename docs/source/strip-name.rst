.. _strip_namepy--bulk-remove-text-from-filenames:

strip_name.py — bulk-remove text from filenames
===============================================

``strip_name.py`` scans a folder and **removes a chosen piece of text from every
filename**, keeping the rest of the name (and the extension) untouched. It is
built for tidying downloaded course files that all carry the same site tag, for
example turning ``01 Intro-somesite.com.mp4`` into ``01 Intro.mp4``.

The script lives at ``strip_name.py`` in the toolkit root.

.. tip::

   Nothing is renamed until you add ``--apply``. Without it, the script only
   **previews** the ``old -> new`` changes so you can check them first.

Quick start
-----------

.. code:: powershell

   # 1. Preview (changes nothing) — show what would be renamed
   python strip_name.py "C:\Courses\MyCourse" "[SomeSite.com] - "

   # 2. If the preview looks right, do it for real
   python strip_name.py "C:\Courses\MyCourse" "[SomeSite.com] - " --apply

Example result:

================================= ==============================
Before                            After
================================= ==============================
``[SomeSite.com] - 01 Intro.mp4`` ``01 Intro.mp4``
``[SomeSite.com] - 02 Setup.mp4`` ``02 Setup.mp4``
``03 Bonus.mp4`` *(no match)*     ``03 Bonus.mp4`` *(untouched)*
================================= ==============================

Options
-------

+---------------------------+-----------------------------------------+
| Flag                      | What it does                            |
+===========================+=========================================+
| *(none)*                  | **Dry-run** — prints every              |
|                           | ``old -> new``, renames nothing         |
+---------------------------+-----------------------------------------+
| ``--apply``               | Actually performs the renames           |
+---------------------------+-----------------------------------------+
| ``-r``, ``--recursive``   | Also scan sub-folders                   |
+---------------------------+-----------------------------------------+
| ``--ext .mp4 --ext .srt`` | Only touch these extensions             |
|                           | (repeatable)                            |
+---------------------------+-----------------------------------------+
| ``--ignore-case``         | Match the text regardless of            |
|                           | upper/lower case                        |
+---------------------------+-----------------------------------------+
| ``--tidy``                | Collapse leftover double-spaces and     |
|                           | trim stray ``-``, ``_``, ``.``, spaces  |
|                           | at the ends                             |
+---------------------------+-----------------------------------------+

When the text starts with a dash
--------------------------------

If the text you want to remove **begins with ``-``** (e.g. ``-test.com``), the
command line treats it as an option flag and you get a usage error — even inside
quotes. Put ``--`` before the folder and text so everything after it is read
literally:

.. code:: powershell

   python strip_name.py --tidy -- "C:\Courses\MyCourse" "-test.com"
   python strip_name.py --tidy --apply -- "C:\Courses\MyCourse" "-test.com"

The order is always: ``python strip_name.py [options] -- FOLDER TEXT``.

Worked example
--------------

Starting folder:

::

   01 Intro-test.com.mp4
   02 Setup-test.com.mp4
   03 Deep Dive-test.com.mp4
   04 No Suffix.mp4

Preview:

.. code:: powershell

   python strip_name.py --tidy -- "C:\Courses\Demo" "-test.com"

::

     01 Intro-test.com.mp4
       -> 01 Intro.mp4
     02 Setup-test.com.mp4
       -> 02 Setup.mp4
     03 Deep Dive-test.com.mp4
       -> 03 Deep Dive.mp4

   3 file(s) would rename (dry-run) | 0 collision(s) skipped | 0 empty-name skipped
   Re-run with --apply to perform the rename.

Apply with ``--apply`` and the folder becomes:

::

   01 Intro.mp4
   02 Setup.mp4
   03 Deep Dive.mp4
   04 No Suffix.mp4        <- untouched, it never contained the text

Note how ``--tidy`` removed the trailing ``-`` left behind, giving ``01 Intro.mp4``
rather than ``01 Intro-.mp4``.

Built-in safety
---------------

- **Extensions are never changed** — only the name part is edited.
- **Collisions are skipped** — if removing the text would produce a filename
  that already exists (or that another file in the same run would also produce),
  the script reports it and leaves both files alone.
- **Empty names are skipped** — it will not create a file whose name would be
  blank after removal.
- **Non-matching files are ignored** — a file that does not contain the text is
  left exactly as-is.

Summary line
------------

Every run ends with a one-line tally so you know what happened:

::

   3 file(s) RENAMED | 0 collision(s) skipped | 0 empty-name skipped

In dry-run mode this reads ``would rename (dry-run)`` instead of ``RENAMED``.
