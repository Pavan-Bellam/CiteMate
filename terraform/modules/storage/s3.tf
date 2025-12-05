resource "aws_s3_object" "folders" {
  for_each = toset(var.folders)

  bucket = var.bucket_name
  key    = "${var.prefix}/${each.value}/"
}
