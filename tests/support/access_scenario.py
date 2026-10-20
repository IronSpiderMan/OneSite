"""Executed in the generated backend directory by the integration test."""
import asyncio

from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from app.main import app
from app.core.db import engine, init_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.entities import (
    SecretRecord, ReadOnlyRecord, OwnedFolder, VisibleTag, FolderTag,
    PrivateTag, FolderPrivateTag, InlineChild,
)


def auth(id):
    return {'Authorization': f'Bearer {create_access_token(id)}'}


async def main():
    await init_db()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([
            User(id=1,email='user@example.test',hashed_password=get_password_hash('before'),role=UserRole.USER,private_note='staff only'),
            User(id=2,email='other@example.test',hashed_password='',role=UserRole.USER),
            User(id=3,email='admin@example.test',hashed_password='',role=UserRole.ADMIN),
            User(id=4,email='dev@example.test',hashed_password='',role=UserRole.DEVELOPER),
            SecretRecord(id=1,title='visible',secret='hidden'), ReadOnlyRecord(id=1),
            OwnedFolder(id=1,owner_id=1,code='mine',batch='a'),
            OwnedFolder(id=2,owner_id=2,code='other',batch='b'),
            VisibleTag(id=1,owner_id=1,title='mine'), VisibleTag(id=2,owner_id=2,title='other'),
            FolderTag(folder_id=1,tag_id=1),FolderTag(folder_id=1,tag_id=2),FolderTag(folder_id=2,tag_id=2),
            InlineChild(id=1,owner_id=2,folder_id=2,title='other'),
            PrivateTag(id=1,title='private'),FolderPrivateTag(folder_id=1,tag_id=1),
        ])
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        response = await client.get('/api/v1/users/me', headers=auth(1))
        assert response.status_code == 200, response.text
        assert 'private_note' not in response.json(), response.text
        response = await client.put('/api/v1/users/me', headers=auth(1), json={'private_note':'tampered'})
        assert response.status_code == 403, response.text
        response = await client.put('/api/v1/users/me', headers=auth(1), json={'full_name':'New Name', 'old_password':'before', 'password':'after'})
        assert response.status_code == 200, response.text
        assert response.json()['full_name'] == 'New Name', response.text
        response = await client.post('/api/v1/login/access-token', data={'username':'user@example.test', 'password':'after'})
        assert response.status_code == 200, response.text
        from app.services.system_config import service as config_service
        from app.schemas.system_config import SystemConfigUpdate
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await config_service.update(session, SystemConfigUpdate(allow_registration=True))
        response = await client.post('/api/v1/register', json={'email':'new@example.test','password':'new password'})
        assert response.status_code == 201, response.text
        assert 'private_note' not in response.json(), response.text
        for user in (3,4):
            response=await client.post('/api/v1/secret_records/',headers=auth(user),json={'title':'denied'})
            assert response.status_code==403,response.text
        for user in (1,3,4):
            for method,path,body in [('post','/api/v1/read_only_records/',{}),('put','/api/v1/read_only_records/1',{}),('delete','/api/v1/read_only_records/1',None)]:
                response=await client.request(method,path,headers=auth(user),json=body)
                assert response.status_code==403,response.text
        for path in ('/api/v1/secret_records/1','/api/v1/secret_records/'):
            response=await client.get(path,headers=auth(1))
            assert response.status_code==200,response.text
            data=response.json()
            data=data['items'][0] if 'items' in data else data
            assert 'secret' not in data,data
            response=await client.get(path,headers=auth(3))
            assert response.status_code==200,response.text
            data=response.json()
            data=data['items'][0] if 'items' in data else data
            assert data['secret']=='hidden',data
        response=await client.put('/api/v1/secret_records/1',headers=auth(1),json={'secret':'tampered'})
        assert response.status_code==403,response.text
        response=await client.post('/api/v1/secret_records/',headers=auth(1),json={'title':'valid'})
        assert response.status_code==200,response.text
        assert 'secret' not in response.json()
        response=await client.post('/api/v1/submit_onlys/',headers=auth(1),json={'title':'accepted'})
        assert response.status_code==200,response.text
        assert (await client.get('/api/v1/submit_onlys/',headers=auth(1))).status_code==403
        for path in ('/api/v1/owned_folders/2','/api/v1/owned_folders/by_code_batch?code=other&batch=b','/api/v1/owned_folders/2/visible_tags'):
            response=await client.get(path,headers=auth(1))
            assert response.status_code==404,(path,response.text)
        response=await client.get('/api/v1/owned_folders/by_code_batch?code=mine&batch=a',headers=auth(1))
        assert response.status_code==200,response.text
        response=await client.get('/api/v1/owned_folders/1/visible_tags',headers=auth(1))
        assert response.status_code==200,response.text
        assert response.json()['total']==1,response.text
        assert response.json()['items'][0]['id']==1,response.text
        assert 'title' not in response.json()['items'][0], response.text
        response=await client.get('/api/v1/owned_folders/1/visible_tags_with_meta',headers=auth(1))
        assert response.status_code==200,response.text
        assert response.json()['total']==1,response.text
        assert 'label' not in response.json()['items'][0],response.text
        response=await client.get('/api/v1/owned_folders/1/private_tags',headers=auth(1))
        assert response.status_code==403,response.text
        response=await client.put('/api/v1/owned_folders/1',headers=auth(1),json={'inline_childs':[{'id':1,'title':'stolen'}]})
        assert response.status_code==404,response.text
        response=await client.put('/api/v1/owned_folders/1',headers=auth(1),json={'inline_childs':[{'title':'child','secret':'tampered'}]})
        assert response.status_code==403,response.text
        response=await client.put('/api/v1/owned_folders/1',headers=auth(1),json={'inline_childs':[{'title':'child'}]})
        assert response.status_code==200,response.text
        response=await client.post('/api/v1/owned_folders/',headers=auth(1),json={'code':'new','batch':'new'})
        assert response.status_code==200,response.text
        assert response.json()['owner_id']==1,response.text
        response=await client.post('/api/v1/upload',files={'file':('test.txt',b'content')})
        assert response.status_code==401,response.text
        response=await client.post('/api/v1/upload',headers=auth(1),files={'file':('test.txt',b'content')})
        assert response.status_code==200,response.text
        public=await client.get(response.json()['url'])
        assert public.status_code==200 and public.content==b'content'
    await engine.dispose()


asyncio.run(main())
