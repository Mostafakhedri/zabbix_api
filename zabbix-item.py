#!/usr/bin/env python
import os, sys
import argparse

try:
        import configparser
except:
        from six.moves import configparser

try:
    from zabbix_api import ZabbixAPI
except:
    print("Error: Zabbix API library must be installed: pip install zabbix-api.",
          file=sys.stderr)
    sys.exit(1)

try:
    import json
except:
    import simplejson as json


import requests


class ZabbixInventory(object):

    def read_settings(self):
        config = configparser.ConfigParser()
        conf_path = 'path to zabbix.ini\\zabbix.ini'
        if not os.path.exists(conf_path):
	        conf_path = os.path.dirname(os.path.realpath(__file__)) + '/zabbix.ini'
        if os.path.exists(conf_path):
	        config.read(conf_path)
        # server
        if config.has_option('zabbix', 'server'):
            self.zabbix_server = config.get('zabbix', 'server')

        # login
        if config.has_option('zabbix', 'username'):
            self.zabbix_username = config.get('zabbix', 'username')
        if config.has_option('zabbix', 'password'):
            self.zabbix_password = config.get('zabbix', 'password')

    def read_cli(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--host', action='store_true')
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--item', action='store_true')
        parser.add_argument('--dele', action='store_true')
        parser.add_argument('--show', action='store_true')
        parser.add_argument('--addt', action='store_true')
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--confluence', action='store_true')


        self.options = parser.parse_args()

    def hoststub(self):
        return {
            'hosts': []
        }
    
    def hoststub_host(self, host):
        return {
            host : []
        }

   

    def get_item(self, api):
        raw_data = api.item.get({'output': ['name', 'itemid'], 'selectItemDiscovery': ['itemid']})
        get_data = []
        for raw in raw_data:
            if raw['itemDiscovery']:
                get_data.append(raw['itemDiscovery']['itemid'])
        return get_data            

    def rm_item(self, api):
        rm = api.item.delete(self.get_item(api))
        return rm


    def show_host(self, api):
        s = []
        raw_data = api.host.get({'output': 'hostid'})
        for i in raw_data:
            s.append(i['hostid'])
        print(s)


    def add_template(self, api):
        raw_data = api.host.get({'output': 'hostid'})
        for i in raw_data:
            s = i['hostid']
            add = api.template.massadd({
                "templates": { "templateid": "10505" }, 
                "hosts": [{"hostid": s }]
            })
            print(s)
        print("the template adding is complete ")
        


    def all_item(self, api, host_id):
        raw_data = api.item.get({'output': ['name', 'itemid', 'key_', 'description'], 'selectTriggers': '', 'hostids': host_id})
        for raw in raw_data:
            if raw['triggers']:
                for rawt in raw['triggers']:
                    if rawt['triggerid']:
                        item = raw['itemid']
                        raw_data2 = api.trigger.get({'output': ['expression', 'description'], 'selectFunctions': 'extend', 'itemids': item})
                        
                        raw['triggers'] = raw_data2 
        return raw_data

    def get_host(self, api):
        raw_data = api.hostgroup.get({'output': 'extend', 'selectHosts': 'extend'})
        data = dict()
        hosts = dict()
        for hostgroup in raw_data:
            groupname = hostgroup['name']
            data[groupname] = self.hoststub()
            for hostname in hostgroup['hosts']:
                host_id = hostname['hostid']
                if host_id in hosts:
                    host = hosts[host_id]
                else:
                    host_name = hostname['host']
                    host_info = self.all_item(api, host_id)
                    host = {
                        'id': host_id,
                        'name': host_name,
                        'info': host_info
                    }
                    hosts[host_id] = host
                data[groupname]['hosts'].append(host)
            return data
   
    def confluence(self):
        credentials = configparser.ConfigParser()
        credentials.read('./confluence.ini')
        user = credentials.get('confluence','user')
        password = credentials.get('confluence','password')
        auth = (user, password)      
        with open('newout.json', 'r', encoding='utf-8') as file:
            out = json.load(file)
            
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        environment="Zabbix Trigger Documentation"
        
        table = [
            'Item Name',
            'Key',
            'Description',
            'Trigger Name',
            'Exp',
            'Function',
            'Severity',
            'Action'
        ]
        
        with open('confluence_table.html', 'w', encoding='utf-8') as f1:
            html = """<html> <h3>This page is generated MOSTAFA KHEDRI</h3><table border="0">"""
            html += "<tr>"

            for x in table:
                html += "<td>"+x+"</td>"
            html += "</tr>"
    
            for i in out:
                for k, v in i.items():
                    html += "<tr><td><h1>"+k+"</h1></td>"
                    for g in v['hosts']:
                        html += "<td><h1>"+g['name']+"</h1></td></tr>"
                        for m in g['info']:
                            html += "<td>"+m['name']+"</td><td>"+m['key_']+"</td><td>"+m['description']+"</td>"
                            if len(m['triggers']) == 1:
                                for l in m['triggers']:
                                    html += "<td>"+l['description']+"</td><td>"+l['expression']+"</td>"
                                    for b in l['functions']:
                                        html += "<td>"+b['function']+"</td><td>disaster</td><td>some action</td></tr>"
                            elif len(m['triggers']) > 1:
                                for l in m['triggers']:
                                    html += "<td>"+l['description']+"</td><td>"+l['expression']+"</td>"
                                    for b in l['functions']:
                                        html += "<td>"+b['function']+"</td><td>disaster</td><td>some action</td></tr>"
                                        html += "<tr><td></td><td></td><td></td>"
                                html += "</tr>"
                            else:
                                html += "</tr>"            
                
                html += "</table></html>"
                f1.write(''.join(html))
                
        
        
        params = {'spaceKey': 'some page', 'title': environment}
        result = requests.get("https://one-server/rest/api/content/", headers=headers, auth=auth, params=params)
        json_output = json.loads(result.text)
        if json_output['results']:
            pid = json_output['results'][0]['id']
            print("Updating: https://one-server/display" + environment)
        
        else:
            data = {
                'title': environment,
                'type': 'page',
                'space': {'key': 'some space'}, 
                'ancestors': [{'id': '00000000'}] 
            }
            result = requests.post("https://one-server/rest/api/content/", headers=headers, auth=auth, json=data)
            json_output = json.loads(result.text)
            pid = json_output['id']
            print("Creating: https://one-server/display/" + environment)
        
        result = requests.get("https://confluence.snapp.ir/rest/api/content/"+pid, headers=headers, auth=auth)
        json_output = json.loads(result.text)
        version = json_output['version']['number']
        
        data = {
                'type': 'page',
                'title': environment,
                'body': {
                    'storage': {
                        'value': html,
                        'representation': 'storage',
                    }
                },
                'version': {
                    'number': version + 1,
                    "minorEdit": True 
                }
        }
        
        result = requests.put("https://one-server/rest/api/content/"+pid, headers=headers, auth=auth, json=data)
    



    
    def __init__(self):

        self.defaultgroup = 'group_all'
        self.zabbix_server = None
        self.zabbix_username = None
        self.zabbix_password = None

        self.read_settings()
        self.read_cli()

        if self.zabbix_server and self.zabbix_username:
            try:
                api = ZabbixAPI(server=self.zabbix_server)
                api.login(user=self.zabbix_username, password=self.zabbix_password)
            except BaseException as e:
                print("Error: Could not login to Zabbix server. Check your zabbix.ini.", file=sys.stderr)
                sys.exit(1)

            if self.options.host:
                data = self.get_host(api)
                print(json.dumps(data, indent=2))

            elif self.options.list:
                data = self.get_list(api)
                print(json.dumps(data, indent=2))

            elif self.options.item:
                data = self.get_item(api)
                print(json.dumps(data, indent=2))
            
            elif self.options.dele:
                self.rm_item(api)


            elif self.options.show:
                self.show_host(api)

            elif self.options.addt:
                self.add_template(api)

            elif self.options.all:
                self.all_item(api)

            elif self.options.confluence:
                self.confluence()

            else:
                print("usage: --list  ..OR.. --host  ..OR.. --item ..OR.. --dele ..OR.. --show ..OR.. --addt ..OR.. --all ..OR.. --confluence", file=sys.stderr)
                sys.exit(1)

        else:
            print("Error: Configuration of server and credentials are required. See zabbix.ini.", file=sys.stderr)
            sys.exit(1)

ZabbixInventory()




