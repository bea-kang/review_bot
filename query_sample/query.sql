SELECT 
    pr.id AS review_id,
    pr.contents AS "리뷰본문",
    pr.date_created AT TIME ZONE 'Asia/Seoul' AS "작성일",
    pr.user_account_id AS "작성자ID",
    pra.object_key AS "리뷰이미지_object_key",
    pra._hoodie_file_name AS "리뷰이미지_hoodie",
    ci.name AS "구매상품옵션",
    uab.skin_concern AS "피부고민"
FROM review.product_reviews pr
LEFT JOIN review.product_review_attachments pra 
    ON pr.id = pra.product_review_id
LEFT JOIN catalog.items ci 
    ON pr.product_item_id = ci.id
LEFT JOIN zigzag.user_account_bodies uab 
    ON pr.user_account_id = uab.user_account_id
    AND uab.deprecated = 0
WHERE pr.product_id = 149419525
  AND COALESCE(pr.is_deleted, 0) = 0
  AND COALESCE(pr.is_fraud_deleted, 0) = 0
ORDER BY pr.date_created DESC