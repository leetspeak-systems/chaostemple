
SELECT
	par.parliament_num,
	i.issue_num,
	doc.doc_num,
    u.username,
	COUNT(dos.id)
FROM
	dossier_dossier AS dos
    INNER JOIN althingi_document AS doc ON doc.id = dos.document_id
	INNER JOIN althingi_issue AS i ON i.id = doc.issue_id
	INNER JOIN althingi_parliament AS par ON par.id = i.parliament_id
    INNER JOIN auth_user AS u ON (
		u.id = dos.user_id
        -- AND u.username = 'helgihg'
	)
GROUP BY
	par.parliament_num,
	i.issue_num,
	doc.doc_num,
    u.username
HAVING
	COUNT(dos.id) > 1
