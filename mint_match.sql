SELECT * FROM `gnucash`.`mintexport`;

use gnucash;

create index trx_sig on mintexport (date, original_description(300), transaction_type, amount);

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
