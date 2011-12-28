SELECT * FROM `gnucash`.`mintexport`;

use dm93finance;

select ma.* from
(select distinct account_name from mintexport) ma
left join accounts ga on ga.name = ma.account_name
where ga.name is null
;
select * from mintexport where account_name='Cash';

-- guid column is only 32 chars long
select length(replace(uuid(), '-', ''));

insert into accounts
select replace(uuid(), '-', '') as guid
     , mc.category as name
     , mc.account_type
     , usd.guid as commodity_guid
     , usd.fraction as commodity_scu
     , 0 as non_std_scu
     , parent.guid as parent_guid
     , '' as code
     , '' as description
     , 0 as hidden
     , 0 as placeholder
from (select category, case when tot > 0 then 'INCOME' else 'EXPENSE' end as account_type
   from (
     select category
          , sum(amount * case when transaction_type = 'debit' then -1 else 1 end) as tot
     from mintexport
     group by category) x) mc
join commodities usd on usd.mnemonic='USD'
join accounts parent on parent.name=
   case when mc.account_type = 'EXPENSE' then 'Mint Expenses' else 'Mint Income' end
order by 3, 2;
-- 124 row(s) affected

select distinct slot_type from slots
order by 1;
select * from slots where slot_type=10;
-- 1: int64_val
-- 4: string_val
-- 5: guid_val
-- 6: timespec_val
-- 9: guid_val again?
-- 10: gdate_val

select acct.name, s.*
from accounts acct
join slots s on s.obj_guid = acct.guid
order by 1;

insert into slots (obj_guid, name, slot_type, string_val)
select acct.guid obj_guid
     , 'color' name
     , 4 slot_type
     , 'Not Set' string_val
from accounts parent
join accounts acct on acct.parent_guid = parent.guid
where parent.name='Mint Export';


-- create index trx_sig on mintexport (date, original_description(300), transaction_type, amount);

select count(*), date, original_description, transaction_type, amount
from mintexport
group by date, original_description, transaction_type, amount
having count(*) > 1
order by date desc;

select distinct name from slots;

-- create table mintmatch as
select tx.guid as tx_guid, sp.guid, acct.guid, acct.name, mx.id as mint_id from
transactions tx
join splits sp on sp.tx_guid = tx.guid
join accounts acct on acct.guid = sp.account_guid
join
(
select obj_guid, substring_index(string_val, 'Memo:', -1) as ofx_memo
from slots
where name = 'notes') ofx on ofx.obj_guid = tx.guid
join mintexport mx
on mx.original_description = ofx.ofx_memo
  and timestampdiff(day, tx.post_date, mx.date) = 0;

select count(*) from mintmatch;
select count(*) from mintexport where account_name='PERFORMANCE CHECKING';
select max(post_date) from transactions;

select *
from mintexport mx
left join mintmatch mm on mx.id = mm.mint_id
where mm.mint_id is null;
