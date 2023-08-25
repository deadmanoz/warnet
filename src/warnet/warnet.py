"""
  Warnet is the top-level class for a simulated network.
"""

import docker
import logging
import networkx
import subprocess
import tarfile
import tempfile
import yaml
from pathlib import Path
from tempfile import mkdtemp
from templates import TEMPLATES
from dns import DNS
from warnet.tank import Tank
from warnet.utils import (
    parse_bitcoin_conf
)

TMPDIR_PREFIX = "warnet_tmp_"

class Warnet:
    def __init__(self):
        self.tmpdir = Path(mkdtemp(prefix=TMPDIR_PREFIX))
        self.docker = docker.from_env()
        self.bitcoin_network = "regtest"
        self.docker_network = "warnet"
        self.subnet = "100.0.0.0/8"
        self.graph = None
        self.tanks = []
        logging.info(f"Created Warnet with temp directory {self.tmpdir}")

    @classmethod
    def from_graph_file(cls, graph_file: str, network: str = "warnet"):
        self = cls()
        self.docker_network = network
        self.graph = networkx.read_graphml(graph_file, node_type=int)
        self.tanks_from_graph()
        return self

    @classmethod
    def from_graph(cls, graph):
        self = cls()
        self.graph = graph
        self.tanks_from_graph()
        return self

    def tanks_from_graph(self):
        for node_id in self.graph.nodes():
            if int(node_id) != len(self.tanks):
                raise Exception(f"Node ID in graph must be incrementing integers (got '{node_id}', expected '{len(self.tanks)}')")
            self.tanks.append(Tank.from_graph_node(node_id, self))
        logging.info(f"Imported {len(self.tanks)} tanks from graph")

    def write_bitcoin_confs(self):
        with open(TEMPLATES / "bitcoin.conf", 'r') as file:
            text = file.read()
        base_bitcoin_conf = parse_bitcoin_conf(text)
        for tank in self.tanks:
            tank.write_bitcoin_conf(base_bitcoin_conf)

    def apply_network_conditions(self):
        for tank in self.tanks:
            tank.apply_network_conditions()

    def update_dns_seeds(self):
        """
        Update dns seed list served by dns-seed.

        Currently this is append only, and has no crawl function.
        """
        seeder = self.docker.containers.get("dns-seed")
        records_list = [f"seed.dns-seed.     300 IN  A   {tank.ipv4}" for tank in self.tanks]

        # Using a temp file seems to make docker happier?
        temp_file_path = "/etc/bind/temp_dns_records"
        seeder.exec_run("dns-seed", f"sh -c '> {temp_file_path}'")

        for record in records_list:
            command_to_append = f"sh -c 'echo \"{record}\" >> {temp_file_path}'"
            seeder.exec_run("dns-seed", command_to_append)

        concat_command = f"sh -c 'cat {temp_file_path} >> /etc/bind/dns-seed.zone'"
        seeder.exec_run("dns-seed", concat_command)
        delete_temp_command = f"sh -c 'rm {temp_file_path}'"
        seeder.exec_run("dns-seed", delete_temp_command)

        # Reload bind9 to recognize the changes
        seeder.exec_run("dns-seed", "rndc reload")


    def connect_edges(self):
        for edge in self.graph.edges():
            (src, dst) = edge
            src_tank = self.tanks[int(src)]
            dst_ip = self.tanks[dst].ipv4
            logging.info(f"Using `addndode` to connect tanks {src} to {dst}")
            src_tank.exec(f"bitcoin-cli addnode {dst_ip} add")

    def docker_compose_up(self):
        command = ["docker-compose", "-p", "warnet", "up", "-d", "--build"]
        try:
            with subprocess.Popen(command, cwd=str(self.tmpdir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
                for line in process.stdout:
                    logging.info(line.decode().rstrip())
        except Exception as e:
            logging.error(f"An error occurred while executing `{' '.join(command)}` in {self.tmpdir}: {e}")

    def write_docker_compose(self, dns=True):
        compose = {
            "version": "3.8",
            "networks": {
                self.docker_network: {
                    "name": self.docker_network,
                    "ipam": {
                        "config": [
                            {"subnet": self.subnet}
                        ]
                    }
                }
            },
            "volumes": {
                "grafana-storage": None
            },
            "services": {}
        }

        # Pass services object to each tank so they can add whatever they need.
        for tank in self.tanks:
            tank.add_services(compose["services"])

        # Add global services
        compose["services"]["prometheus"] = {
            "image": "prom/prometheus:latest",
            "container_name": "prometheus",
            "ports": ["9090:9090"],
            "volumes": [f"{self.tmpdir / 'prometheus.yml'}:/etc/prometheus/prometheus.yml"],
            "command": ["--config.file=/etc/prometheus/prometheus.yml"],
            "networks": [
                self.docker_network
            ]
        }
        compose["services"]["node-exporter"] = {
            "image": "prom/node-exporter:latest",
            "container_name": "node-exporter",
            "volumes": [
                "/proc:/host/proc:ro",
                "/sys:/host/sys:ro",
                "/:/rootfs:ro"
            ],
            "command": ["--path.procfs=/host/proc", "--path.sysfs=/host/sys"],
            "networks": [
                self.docker_network
            ]
        }
        compose["services"]["grafana"] = {
            "image": "grafana/grafana:latest",
            "container_name": "grafana",
            "ports": ["3000:3000"],
            "volumes": ["grafana-storage:/var/lib/grafana"],
            "networks": [
                self.docker_network
            ]
        }
        if dns:
            compose["services"]["dns-seed"] = {
                "container_name": "dns-seed",
                "ports": ["15353:53"],
                "volumes": [
                    f"{str(DNS / 'dns-seed.zone')}:/etc/bind/dns-seed.zone",
                    f"{str(DNS / 'named.conf.local')}:/etc/bind/named.conf.local",
                    ],
                "build": {
                    "context": ".",
                    "dockerfile": str(TEMPLATES / "Dockerfile_bind9"),
                },
                "networks": [
                    "warnet"
                ],
            }

        docker_compose_path = self.tmpdir / "docker-compose.yml"
        try:
            with open(docker_compose_path, "w") as file:
                yaml.dump(compose, file)
            logging.info(f"Wrote file: {docker_compose_path}")
        except Exception as e:
            logging.error(f"An error occurred while writing to {docker_compose_path}: {e}")

    def write_prometheus_config(self):
        config = {
            "global": {
                "scrape_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": "prometheus",
                    "scrape_interval": "5s",
                    "static_configs": [{"targets": ["localhost:9090"]}]
                },
                {
                    "job_name": "node-exporter",
                    "scrape_interval": "5s",
                    "static_configs": [{"targets": ["node-exporter:9100"]}]
                },
                {
                    "job_name": "cadvisor",
                    "scrape_interval": "5s",
                    "static_configs": [{"targets": ["cadvisor:8080"]}]
                }
            ]
        }

        for tank in self.tanks:
            tank.add_scrapers(config["scrape_configs"])

        prometheus_path = self.tmpdir / "prometheus.yml"
        try:
            with open(prometheus_path, "w") as file:
                yaml.dump(config, file)
            logging.info(f"Wrote file: {prometheus_path}")
        except Exception as e:
            logging.error(f"An error occurred while writing to {prometheus_path}: {e}")
