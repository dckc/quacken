from django.db import models, connection

class Account(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(max_length=80, null=True)

    def __str__(self):
        return self.name
 
    parent = models.ForeignKey('self', null=True)
 
    kind = models.CharField(max_length=80, null=True)
 

    def balance(self, when):
	"""get account balance as of YYYY-MM-DD
	"""
	# based on snippet 242
	# see also django ticket #3566 re aggregates
	cursor = connection.cursor()
	tables = dict([(x._meta.object_name, x._meta.db_table)
		       for x in Account, Transaction, Split])
	cmd = """select sum(subtot)
	         from %(Split)s, %(Transaction)s, %(Account)s
		 where %(Split)s .trx_id = %(Transaction)s .id
		 and %(Transaction)s .acct_id = %(Account)s .id
		 and %(Account)s .id = %%s
		 and %(Transaction)s . date < %%s
	""" % tables
	cursor.execute(cmd, (self.id, when))
	balrow = cursor.fetchone()
	return balrow[0] or 0

    class Admin:
        pass


class Job(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(max_length=80, null=True)

    def __str__(self):
        return self.name
 

    class Admin:
        pass


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
 
    acct = models.ForeignKey(Account, null=True)
 
    date = models.DateField()
 
    payee = models.CharField(max_length=80, null=True)
 
    num = models.CharField(max_length=80, null=True)
 
    ty = models.CharField(max_length=80, null=True)
 
    s = models.CharField(max_length=80, null=True)
 

    class Admin:
        pass


class Split(models.Model):
    id = models.AutoField(primary_key=True)
 
    trx = models.ForeignKey(Transaction, null=True)
 
    acct = models.ForeignKey(Account, null=True)
 
    job = models.ForeignKey(Job, null=True)
 
    clr = models.CharField(max_length=80, null=True)
 
    memo = models.CharField(max_length=80, null=True)
 
    subtot = models.DecimalField(max_digits=10, decimal_places=2)
 

    class Admin:
        pass


class Payee(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(max_length=80, null=True)

    def __str__(self):
        return self.name
 

    class Admin:
        pass


