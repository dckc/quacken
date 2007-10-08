XSLTPROC=xsltproc

# SQL database schemas from XHTML via OWL, using GRDDL
# Fri, 07 Jan 2005 15:32:50 -0600
# http://lists.w3.org/Archives/Public/public-rdf-in-xhtml-tf/2005Jan/0000.html
OWLSQL=../owlsql


qdb.sql: qdb.owl $(OWLSQL)/owl2sql.xsl
	$(XSLTPROC) --novalid -o $@ $(OWLSQL)/owl2sql.xsl qdb.owl

qdb.owl: qdb.html $(OWLSQL)/grokDBSchema.xsl
	$(XSLTPROC) --novalid -o $@ $(OWLSQL)/grokDBSchema.xsl qdb.html

