SELECT
	vs.vote_casting_type,
	COUNT(DISTINCT vs.vote_casting_type_text) AS desc_count
FROM
	althingi_votecasting AS vs
WHERE
	vs.vote_casting_type != ''
GROUP BY
	vs.vote_casting_type
HAVING
	desc_count > 1
ORDER BY
	vs.vote_casting_type
