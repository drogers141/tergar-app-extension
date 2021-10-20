# tergar-app-extension
Browser extension (Firefox) for the Tergar Meditation App.  This adds the ability to download your
meditation logs and search them locally.

### Two Types of Tergar Courses
Note that internally the Tergar Meditation App distinguishes between two types of Tergar course,
and stores the meditation logs for each in its own array.

- Mala Courses
  - These are for Ngondro courses and the White Tara course
  - They use repetitions of "malas" as the count toward the requirements (e.g. 111,111 for each
  type of Ngondro)
- Regular Courses
  - For all other courses, the amount of time is all that is recorded to mark progress.

Since I am not doing Ngondro, I will not be distinguishing between these as far as storage goes.
The mala course logs will be downloaded and merged with the other logs.  The mala data will be
preserved for any mala courses though, should anyone use this who is doing Ngondro.

