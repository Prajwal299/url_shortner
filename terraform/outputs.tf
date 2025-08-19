output "master_ip" {
  value = aws_instance.master.public_ip
}
output "worker_ips" {
  value = [for inst in aws_instance.worker : inst.public_ip]
}
output "ecr_api_url" {
  value = aws_ecr_repository.api.repository_url
}
output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}