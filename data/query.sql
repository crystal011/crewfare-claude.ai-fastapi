SELECT
  a.ID,
  a.post_title,
  b.meta_value as event_location,
  c.meta_value as event_dates,
  d.meta_value as event_description,
  e.meta_value as event_end_date,
  (
    SELECT t.name
    FROM wp_terms t
    JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
    JOIN wp_term_relationships tr ON tr.term_taxonomy_id = tt.term_taxonomy_id
    WHERE tr.object_id = a.ID
      AND tt.taxonomy = 'event_type'
    LIMIT 1
  ) as event_type,
  (
    SELECT t.name
    FROM wp_terms t
    JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
    JOIN wp_term_relationships tr ON tr.term_taxonomy_id = tt.term_taxonomy_id
    WHERE tr.object_id = a.ID
      AND tt.taxonomy = 'search_categories'
    LIMIT 1
  ) as search_category,
  h.meta_value as event_url
FROM
  wp_posts as a
LEFT JOIN
  wp_postmeta as b on a.ID = b.post_id AND b.meta_key = 'event_location'
LEFT JOIN
  wp_postmeta as c on a.ID = c.post_id AND c.meta_key = 'event_dates'
LEFT JOIN
  wp_postmeta as d on a.ID = d.post_id AND d.meta_key = 'event_description'
LEFT JOIN
  wp_postmeta as e on a.ID = e.post_id AND e.meta_key = 'event_end_date'
LEFT JOIN
  wp_postmeta as h on a.ID = h.post_id AND h.meta_key = 'event_url'
WHERE
  a.post_title LIKE '%'
  AND a.post_type = 'crewfare-events'
  AND a.post_status = 'publish';