use dm93finance;

SET sql_safe_updates=0;

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

