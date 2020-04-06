
Special database considerations
===============================

MySQL
-----

At least one item in Parliament 141 contains a UTF-8 character which might not be storable in MySQL unless the following command is run once the database has been created:

    mysql> ALTER TABLE althingi_committeeagendaitem MODIFY name VARCHAR(300) CHARACTER SET utf8;

It should be safe to do this even after data has been imported. You can either run the aforementioned command yourself, or import the mysql_fix.sql file which should reside in the same directory as these instructions.
