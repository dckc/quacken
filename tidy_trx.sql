use dm93finance;

SET sql_safe_updates=0;
set autocommit=0;

-- clean up BankBV transaction descriptions
update transactions t
join (
select guid, description,
  case
    when description like 'POS Sig Purchase%' 
    then substr(description, length('POS Sig Purchase _'))
    when description like 'POS Pin Purchase%' 
    then substr(description, length('POS Pin Purchase _'))
    when description like 'POS%' 
    then substr(description, length('POS _'))
  end fixed
from transactions
) fx on fx.guid = t.guid
set t.description = fx.fixed
where fx.fixed is not null
;

-- XX6208 POS PURCHASE AT 09/30 04:
-- XX6208 POS PURCHASE AT 09/30 04:54 JCPENNEY 2990 OVERLAND PARK KS 57795546 97164

select * from split_detail
where description like '%POS PURCHASE%';

select * from split_detail
where memo like '%POS PURCHASE%';

select tx.post_date, tx.description, s.memo,
  substr(s.memo, length('XX6208 POS PURCHASE AT 09/30 04:54 _'))
from transactions tx
join splits s on s.tx_guid = tx.guid
where s.memo like '%POS PURCHASE AT%';

update transactions tx
 join splits s on s.tx_guid = tx.guid
set tx.description = substr(s.memo, length('XX6208 POS PURCHASE AT 09/30 04:54 _'))
where tx.description like '%POS PURCHASE AT%';

commit;
