from __future__ import annotations
import argparse
import contextlib
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from mapleos import cli
import stage
import make_profile
import release_gate
import release_assets
import reassemble

class Workspaces(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.project=self.root/'project'; self.project.mkdir()
    def tearDown(self): self.temp.cleanup()
    def args(self,**kw):
        d=dict(project=str(self.project),image='sha256:'+'a'*64,write=False,network=False,allow_env=[],allow_sensitive_files=False,command=['--','bash'])
        d.update(kw); return argparse.Namespace(**d)
    def command(self,**kw): return cli.agent_command(self.args(**kw),uid=1000,gid=1000)
    def test_readonly_by_default(self): self.assertIn(',ro=true',next(x for x in self.command() if x.startswith('type=bind')))
    def test_offline_by_default(self): self.assertIn('--network=none',self.command())
    def test_no_image_pull(self): self.assertIn('--pull=never',self.command())
    def test_no_new_privileges(self): self.assertIn('--security-opt=no-new-privileges',self.command())
    def test_no_capabilities(self): self.assertIn('--cap-drop=all',self.command())
    def test_readonly_root(self): self.assertIn('--read-only',self.command())
    def test_user_namespace(self): self.assertIn('--userns=keep-id',self.command())
    def test_memory_limit(self): self.assertIn('--memory=2g',self.command())
    def test_only_one_host_mount(self): self.assertEqual(self.command().count('--mount'),1)
    def test_no_host_home(self): self.assertNotIn('src='+str(Path.home()),' '.join(self.command()))
    def test_write_explicit(self): self.assertNotIn(',ro=true',next(x for x in self.command(write=True) if x.startswith('type=bind')))
    def test_network_explicit(self): self.assertIn('--network=pasta',self.command(network=True))
    def test_tag_refused(self):
        with self.assertRaises(cli.MapleError): self.command(image='archlinux:latest')
    def test_bad_digest_refused(self):
        with self.assertRaises(cli.MapleError): self.command(image='sha256:abc')
    def test_root_refused(self):
        with self.assertRaises(cli.MapleError): cli.agent_command(self.args(),uid=0,gid=0)
    def test_home_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_project(str(self.root),home=self.root)
    def test_system_root_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_project('/')
    def test_etc_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_project('/etc')
    def test_comma_refused(self):
        p=self.root/'bad,path'; p.mkdir()
        with self.assertRaises(cli.MapleError): cli.validate_project(str(p))
    def test_newline_refused(self):
        p=self.root/'bad\npath'; p.mkdir()
        with self.assertRaises(cli.MapleError): cli.validate_project(str(p))
    def test_symlink_home_refused(self):
        p=self.root/'link'; p.symlink_to(Path.home())
        with self.assertRaises(cli.MapleError): cli.validate_project(str(p))
    def test_sensitive_file_refused(self):
        (self.project/'.env').write_text('EXAMPLE=not-a-key')
        with self.assertRaises(cli.MapleError): self.command()
    def test_explicit_sensitive_override(self):
        (self.project/'.env').write_text('EXAMPLE=not-a-key'); self.assertIn('podman',self.command(allow_sensitive_files=True))
    def test_arbitrary_environment_refused(self):
        with self.assertRaises(cli.MapleError): self.command(allow_env=['SSH_AUTH_SOCK'])
    def test_absent_key_refused(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(cli.MapleError): self.command(allow_env=['OPENAI_API_KEY'])
    def test_key_not_in_argv(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-test-value'}):
            cmd=self.command(allow_env=['OPENAI_API_KEY'])
        self.assertIn('OPENAI_API_KEY',cmd); self.assertNotIn('synthetic-test-value',' '.join(cmd))
    def test_command_not_shell_interpreted(self):
        cmd=self.command(command=['--','echo','x; touch /tmp/not-executed'])
        self.assertEqual(cmd[-1],'x; touch /tmp/not-executed')

class API(unittest.TestCase):
    def test_workbench_noninteractive_returns(self):
        with patch('sys.stdin.isatty', return_value=False), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.workbench(),0)
    def test_https_allowed(self): self.assertEqual(cli.validate_api_url('https://example.com/v1/'),'https://example.com/v1')
    def test_loopback_http(self): cli.validate_api_url('http://127.0.0.1:11434/v1')
    def test_ipv6_loopback_http(self): cli.validate_api_url('http://[::1]:8000/v1')
    def test_invalid_port_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('https://example.com:wrong/v1')
    def test_url_whitespace_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('https://example.com/v1 bad')
    def test_cleartext_remote_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('http://example.com/v1')
    def test_misleading_localhost_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('http://localhost.example.com/v1')
    def test_embedded_credentials_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('https://user:secret@example.com/v1')
    def test_query_refused(self):
        with self.assertRaises(cli.MapleError): cli.validate_api_url('https://example.com/v1?key=example')
    def test_empty_prompt_refused(self):
        with self.assertRaises(cli.MapleError): cli.make_chat_request('',[],'model')
    def test_empty_model_refused(self):
        with self.assertRaises(cli.MapleError): cli.make_chat_request('hi',[],'')
    def test_no_automatic_context(self): self.assertEqual(cli.make_chat_request('hi',[],'model')['messages'][0]['content'],'hi')
    def test_oversized_prompt_refused(self):
        with self.assertRaises(cli.MapleError): cli.make_chat_request('x'*(cli.MAX_CONTEXT_BYTES+1),[],'model')
    def test_file_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'note.txt'; p.write_text('example')
            self.assertIn('Explicit attachment: note.txt',cli.make_chat_request('hi',[str(p)],'model')['messages'][0]['content'])
    def test_binary_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'binary'; p.write_bytes(b'\x00\xff')
            with self.assertRaises(cli.MapleError): cli.make_chat_request('hi',[str(p)],'model')
    def test_oversized_file_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'large'; p.write_bytes(b'x'*(cli.MAX_FILE_BYTES+1))
            with self.assertRaises(cli.MapleError): cli.make_chat_request('hi',[str(p)],'model')
    def test_no_network_without_consent(self):
        a=argparse.Namespace(base_url='https://example.com/v1',prompt='hi',file=[],model='model',yes_send=False)
        with patch('urllib.request.build_opener') as op,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.ask(a),2); op.assert_not_called()
    def test_redirect_refused(self):
        with self.assertRaises(cli.MapleError): cli.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')
    def test_real_loopback_request(self):
        received=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((self.path,json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body=json.dumps({'choices':[{'message':{'content':'Maple loopback test passed'}}]}).encode()
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
            def log_message(self,*args): pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            a=argparse.Namespace(base_url=f'http://127.0.0.1:{server.server_port}/v1',prompt='test',file=[],model='fixture',yes_send=True)
            output=io.StringIO()
            with patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(output): self.assertEqual(cli.ask(a),0)
            self.assertIn('Maple loopback test passed',output.getvalue()); self.assertEqual(received[0][0],'/v1/chat/completions')
        finally: server.shutdown(); server.server_close(); thread.join()

class Sources(unittest.TestCase):
    def test_real_git_object_not_dirty_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); subprocess.run(['git','init','-q',td],check=True); (p/'hello.txt').write_text('pinned')
            subprocess.run(['git','-C',td,'add','.'],check=True)
            subprocess.run(['git','-C',td,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'],check=True)
            sha=subprocess.check_output(['git','-C',td,'rev-parse','HEAD'],text=True).strip()
            (p/'hello.txt').write_text('dirty local change')
            self.assertEqual(stage.tracked_bytes(p,sha,'hello.txt'),b'pinned')
    def test_source_path_traversal_refused(self):
        with self.assertRaises(ValueError): stage.tracked_bytes(Path('.'),'a'*40,'../secret')
    def test_bad_source_pin_refused(self):
        with self.assertRaises(ValueError): stage.tracked_bytes(Path('.'),'main','file')
    def test_profile_drops_autologin_and_ssh(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); up=base/'up'; up.mkdir(); (up/'airootfs/root').mkdir(parents=True)
            (up/'airootfs/root/.automated_script.sh').write_text('must disappear')
            (up/'airootfs/etc/systemd/system/getty@tty1.service.d').mkdir(parents=True)
            (up/'airootfs/etc/systemd/system/getty@tty1.service.d/autologin.conf').write_text('root autologin')
            (up/'profiledef.sh').write_text("bootmodes=('bios.syslinux'\n 'uefi.systemd-boot')\n")
            (up/'pacman.conf').write_text('[options]\nSigLevel = Required DatabaseOptional\n')
            (up/'packages.x86_64').write_text('base\nlinux\n')
            repo=base/'repo'; repo.mkdir(); pkg=repo/'mapleos-core.pkg.tar.zst'; pkg.write_bytes(b'fixture-not-a-real-package')
            out=base/'profile'; make_profile.make_profile(up,out,repo,pkg)
            live=out/'airootfs'
            self.assertFalse((live/'root/.automated_script.sh').exists())
            self.assertFalse((live/'etc/systemd/system/getty@tty1.service.d/autologin.conf').exists())
            self.assertEqual(os.readlink(live/'etc/systemd/system/sshd.service'),'/dev/null')
            self.assertTrue((live/'etc/shadow').read_text().startswith('root:!:'))
            self.assertEqual((live/'etc/machine-id').read_bytes(),b'')
            self.assertIn('SigLevel = Required DatabaseOptional',(out/'pacman.conf').read_text())
            subprocess.run(['bash','-n',str(out/'profiledef.sh')],check=True)
    def test_profile_preserves_pacman_keyring_init(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            up=base/"up"
            system=up/"airootfs/etc/systemd/system"
            wants=system/"multi-user.target.wants"
            wants.mkdir(parents=True)

            (system/"pacman-init.service").write_text("")
            (system/"etc-pacman.d-gnupg.mount").write_text("")
            (wants/"pacman-init.service").symlink_to("../pacman-init.service")

            (up/"profiledef.sh").write_text(
                "bootmodes=(bios.syslinux uefi.systemd-boot)" + chr(10)
            )
            (up/"pacman.conf").write_text(
                "[options]" + chr(10) +
                "SigLevel = Required DatabaseOptional" + chr(10)
            )
            (up/"packages.x86_64").write_text(
                "base" + chr(10) + "linux" + chr(10)
            )

            repo=base/"repo"
            repo.mkdir()
            pkg=repo/"mapleos-core.pkg.tar.zst"
            pkg.write_bytes(b"fixture-not-a-real-package")

            out=base/"profile"
            make_profile.make_profile(up,out,repo,pkg)

            generated=out/"airootfs/etc/systemd/system"

            self.assertTrue(
                (generated/"pacman-init.service").is_file()
            )
            self.assertTrue(
                (generated/"etc-pacman.d-gnupg.mount").is_file()
            )

            link=generated/"multi-user.target.wants/pacman-init.service"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), "../pacman-init.service")

    def test_changed_archiso_api_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            up=Path(td)/'up'; up.mkdir(); (up/'profiledef.sh').write_text('bootmodes=(unknown)')
            with self.assertRaises(ValueError): make_profile.make_profile(up,Path(td)/'out',Path(td),Path(td)/'x')

class Release(unittest.TestCase):
    def test_pending_qa_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            iso=Path(td)/'test.iso'; iso.write_bytes(b'fixture')
            self.assertTrue(release_gate.check(iso,{}, {}, {}))
    def test_exact_iso_evidence_required(self):
        with tempfile.TemporaryDirectory() as td:
            iso=Path(td)/'test.iso'; iso.write_bytes(b'fixture'); sha=hashlib.sha256(b'fixture').hexdigest()
            build={'iso':{'sha256':sha},'source_tree_sha256':'source'}
            boots={'iso_sha256':sha,'results':[{'mode':'bios','passed':True},{'mode':'uefi','passed':True}]}
            qa={'iso_sha256':sha,'source_tree_sha256':'source','reviewer':'synthetic fixture','reviewed_utc':'fixture','checks':{x:True for x in release_gate.REQUIRED}}
            self.assertEqual(release_gate.check(iso,build,boots,qa),[])
            iso.write_bytes(b'changed'); self.assertTrue(release_gate.check(iso,build,boots,qa))
    def test_uefi_missing_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            iso=Path(td)/'test.iso'; iso.write_bytes(b'x')
            self.assertTrue(any('UEFI' in x for x in release_gate.check(iso,{}, {'results':[{'mode':'bios','passed':True}]}, {})))
    def test_single_file_export_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); iso=p/'test.iso'; iso.write_bytes(b'not-a-real-iso')
            release_assets.export(iso,p/'release'); result=reassemble.reassemble(p/'release')
            self.assertEqual(result.read_bytes(),iso.read_bytes())
    def test_multipart_reassembly(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); data=b'abcdef'; parts=[]
            for i,chunk in enumerate((b'abc',b'def')):
                name=f'test.iso.part{i:03d}'; (p/name).write_bytes(chunk)
                parts.append({'name':name,'bytes':len(chunk),'sha256':hashlib.sha256(chunk).hexdigest()})
            (p/'ISO-MANIFEST.json').write_text(json.dumps({'name':'test.iso','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'parts':parts}))
            self.assertEqual(reassemble.reassemble(p).read_bytes(),data)
    def test_existing_assembly_temp_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); data=b'abc'; (p/'part').write_bytes(data)
            (p/'test.iso.assembling').write_bytes(b'keep-existing-file')
            (p/'ISO-MANIFEST.json').write_text(json.dumps({'name':'test.iso','bytes':3,'sha256':hashlib.sha256(data).hexdigest(),'parts':[{'name':'part','bytes':3,'sha256':hashlib.sha256(data).hexdigest()}]}))
            with self.assertRaises(FileExistsError): reassemble.reassemble(p)
            self.assertEqual((p/'test.iso.assembling').read_bytes(),b'keep-existing-file')
    def test_traversal_in_manifest_refused(self):
        with self.assertRaises(ValueError): reassemble.name_only('../outside')
    def test_absolute_manifest_path_refused(self):
        with self.assertRaises(ValueError): reassemble.name_only('/tmp/outside')
    def test_corrupt_part_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'part').write_bytes(b'wrong')
            (p/'ISO-MANIFEST.json').write_text(json.dumps({'name':'test.iso','sha256':'a'*64,'bytes':5,'parts':[{'name':'part','sha256':'b'*64,'bytes':5}]}))
            with self.assertRaises(ValueError): reassemble.reassemble(p)

if __name__=='__main__': unittest.main()
