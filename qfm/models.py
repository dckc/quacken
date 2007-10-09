from django.db import models

class Account(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(maxlength=80, null=True)

    def __str__(self):
        return self.name
 
    parent = models.ForeignKey('self', null=True)
 

    class Admin:
        pass


class Job(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(maxlength=80, null=True)

    def __str__(self):
        return self.name
 

    class Admin:
        pass


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
 
    acct = models.ForeignKey(Account, null=True)
 
    date = models.DateField()
 
    payee = models.CharField(maxlength=80, null=True)
 
    num = models.CharField(maxlength=80, null=True)
 
    ty = models.CharField(maxlength=80, null=True)
 
    memo = models.CharField(maxlength=80, null=True)
 

    class Admin:
        pass


class Split(models.Model):
    id = models.AutoField(primary_key=True)
 
    trx = models.ForeignKey(Transaction, null=True)
 
    acct = models.ForeignKey(Account, null=True)
 
    job = models.ForeignKey(Job, null=True)
 
    clr = models.CharField(maxlength=80, null=True)
 
    memo = models.CharField(maxlength=80, null=True)
 
    subtot = models.FloatField(max_digits=10, decimal_places=2)
 

    class Admin:
        pass


class Payee(models.Model):
    id = models.AutoField(primary_key=True)
 
    name = models.CharField(maxlength=80, null=True)

    def __str__(self):
        return self.name
 

    class Admin:
        pass


