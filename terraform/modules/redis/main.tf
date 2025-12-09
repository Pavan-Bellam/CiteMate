resource "upstash_redis_database" "this" {
    database_name  = var.redis_db_name
    region         = "global"
    primary_region = var.redis_primary_region
    tls            = var.redis_tls
}