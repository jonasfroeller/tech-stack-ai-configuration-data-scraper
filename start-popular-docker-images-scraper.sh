#!/bin/bash

queries=(
  "node"
  "python"
  "rails"
  "openjdk"
  "django"
  "react"
  "angular"
  "vue"
  "svelte"
  "next"
  "postgres"
  "mysql"
  "mongo"
  "redis"
  "sqlite"
  "java"
  "ruby"
  "php"
  "golang"
  "flask"
  "rabbitmq"
  "kafka"
  "nats"
  "memcached"
  "jenkins"
  "gitlab-runner"
  "drone"
  "prom/prometheus"
  "grafana"
  "elasticsearch"
  "logstash"
  "kibana"
  "kubernetes"
  "swarm"
  "nomad"

)

for query in "${queries[@]}"; do
  echo "Running Scrapy for Docker image: $query"
  scrapy crawl dockerhubQueriedRegistrySpider -a query="$query"
done