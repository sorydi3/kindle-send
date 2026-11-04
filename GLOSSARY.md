# Glossary

**Book**: an ebook file already on the local disk (EPUB, PDF, MOBI, AZW3, ...). Finding or downloading books is not part of this project.

**Kindle**: the single e-reader device the user sends Books to.

**Kindle address**: the `@kindle.com` email address Amazon assigns to the Kindle.

**Approved sender**: an email address on Amazon's list of addresses allowed to email the Kindle address.

**Send**: one request to deliver one or more Books to the Kindle.

**Route**: how a Send reaches the Kindle. Either **Email route** (attachment to the Kindle address) or **USB route** (copying onto the Kindle while it is plugged in).

**Email limit**: the largest Book the Email route can carry. Set by Gmail, not Amazon.

**Pending Send**: a Book whose USB Route is waiting for the Kindle to be plugged in. Forgotten if the shell restarts.

**Conversion**: making a Kindle-readable copy of a Book (EPUB to AZW3) so it can take the USB Route. The original Book is never changed.

**Book folders**: the folders the picker looks in for Books. Books outside them are sent from the file manager instead.

**Send limit**: the plugin's own cap on how often it emails the Kindle address, kept below Amazon's unpublished throttle. Books over the limit wait their turn.
