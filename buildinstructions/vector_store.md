Vector stores
Beta

Vector stores are used to store files for use by the file_search tool.

Related guide: File Search
Create vector store
Beta
post https://api.openai.com/v1/vector_stores

Create a vector store.
Request body
file_ids

array
Optional

A list of File IDs that the vector store should use. Useful for tools like file_search that can access files.
name

string
Optional

The name of the vector store.
expires_after

object
Optional

The expiration policy for a vector store.
chunking_strategy

object
Optional

The chunking strategy used to chunk the file(s). If not set, will use the auto strategy. Only applicable if file_ids is non-empty.
metadata

map
Optional

Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format. Keys can be a maximum of 64 characters long and values can be a maximum of 512 characters long.
Returns

A vector store object.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStore = await openai.beta.vectorStores.create({
    name: "Support FAQ"
  });
  console.log(vectorStore);
}

main();

Response

{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776,
  "name": "Support FAQ",
  "bytes": 139920,
  "file_counts": {
    "in_progress": 0,
    "completed": 3,
    "failed": 0,
    "cancelled": 0,
    "total": 3
  }
}

List vector stores
Beta
get https://api.openai.com/v1/vector_stores

Returns a list of vector stores.
Query parameters
limit

integer
Optional
Defaults to 20

A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.
order

string
Optional
Defaults to desc

Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
after

string
Optional

A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
before

string
Optional

A cursor for use in pagination. before is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.
Returns

A list of vector store objects.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStores = await openai.beta.vectorStores.list();
  console.log(vectorStores);
}

main();

Response

{
  "object": "list",
  "data": [
    {
      "id": "vs_abc123",
      "object": "vector_store",
      "created_at": 1699061776,
      "name": "Support FAQ",
      "bytes": 139920,
      "file_counts": {
        "in_progress": 0,
        "completed": 3,
        "failed": 0,
        "cancelled": 0,
        "total": 3
      }
    },
    {
      "id": "vs_abc456",
      "object": "vector_store",
      "created_at": 1699061776,
      "name": "Support FAQ v2",
      "bytes": 139920,
      "file_counts": {
        "in_progress": 0,
        "completed": 3,
        "failed": 0,
        "cancelled": 0,
        "total": 3
      }
    }
  ],
  "first_id": "vs_abc123",
  "last_id": "vs_abc456",
  "has_more": false
}

Retrieve vector store
Beta
get https://api.openai.com/v1/vector_stores/{vector_store_id}

Retrieves a vector store.
Path parameters
vector_store_id

string
Required

The ID of the vector store to retrieve.
Returns

The vector store object matching the specified ID.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStore = await openai.beta.vectorStores.retrieve(
    "vs_abc123"
  );
  console.log(vectorStore);
}

main();

Response

{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776
}

Modify vector store
Beta
post https://api.openai.com/v1/vector_stores/{vector_store_id}

Modifies a vector store.
Path parameters
vector_store_id

string
Required

The ID of the vector store to modify.
Request body
name

string or null
Optional

The name of the vector store.
expires_after

object
Optional

The expiration policy for a vector store.
metadata

map
Optional

Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format. Keys can be a maximum of 64 characters long and values can be a maximum of 512 characters long.
Returns

The modified vector store object.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStore = await openai.beta.vectorStores.update(
    "vs_abc123",
    {
      name: "Support FAQ"
    }
  );
  console.log(vectorStore);
}

main();

Response

{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776,
  "name": "Support FAQ",
  "bytes": 139920,
  "file_counts": {
    "in_progress": 0,
    "completed": 3,
    "failed": 0,
    "cancelled": 0,
    "total": 3
  }
}

Delete vector store
Beta
delete https://api.openai.com/v1/vector_stores/{vector_store_id}

Delete a vector store.
Path parameters
vector_store_id

string
Required

The ID of the vector store to delete.
Returns

Deletion status
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const deletedVectorStore = await openai.beta.vectorStores.del(
    "vs_abc123"
  );
  console.log(deletedVectorStore);
}

main();

Response

{
  id: "vs_abc123",
  object: "vector_store.deleted",
  deleted: true
}

The vector store object
Beta

A vector store is a collection of processed files can be used by the file_search tool.
id

string

The identifier, which can be referenced in API endpoints.
object

string

The object type, which is always vector_store.
created_at

integer

The Unix timestamp (in seconds) for when the vector store was created.
name

string

The name of the vector store.
usage_bytes

integer

The total number of bytes used by the files in the vector store.
file_counts

object
status

string

The status of the vector store, which can be either expired, in_progress, or completed. A status of completed indicates that the vector store is ready for use.
expires_after

object

The expiration policy for a vector store.
expires_at

integer or null

The Unix timestamp (in seconds) for when the vector store will expire.
last_active_at

integer or null

The Unix timestamp (in seconds) for when the vector store was last active.
metadata

map

Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format. Keys can be a maximum of 64 characters long and values can be a maximum of 512 characters long.
OBJECT The vector store object

{
  "id": "vs_123",
  "object": "vector_store",
  "created_at": 1698107661,
  "usage_bytes": 123456,
  "last_active_at": 1698107661,
  "name": "my_vector_store",
  "status": "completed",
  "file_counts": {
    "in_progress": 0,
    "completed": 100,
    "cancelled": 0,
    "failed": 0,
    "total": 100
  },
  "metadata": {},
  "last_used_at": 1698107661
}

Vector store files
Beta

Vector store files represent files inside a vector store.

Related guide: File Search
Create vector store file
Beta
post https://api.openai.com/v1/vector_stores/{vector_store_id}/files

Create a vector store file by attaching a File to a vector store.
Path parameters
vector_store_id

string
Required

The ID of the vector store for which to create a File.
Request body
file_id

string
Required

A File ID that the vector store should use. Useful for tools like file_search that can access files.
chunking_strategy

object
Optional

The chunking strategy used to chunk the file(s). If not set, will use the auto strategy.
Returns

A vector store file object.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const myVectorStoreFile = await openai.beta.vectorStores.files.create(
    "vs_abc123",
    {
      file_id: "file-abc123"
    }
  );
  console.log(myVectorStoreFile);
}

main();

Response

{
  "id": "file-abc123",
  "object": "vector_store.file",
  "created_at": 1699061776,
  "usage_bytes": 1234,
  "vector_store_id": "vs_abcd",
  "status": "completed",
  "last_error": null
}

List vector store files
Beta
get https://api.openai.com/v1/vector_stores/{vector_store_id}/files

Returns a list of vector store files.
Path parameters
vector_store_id

string
Required

The ID of the vector store that the files belong to.
Query parameters
limit

integer
Optional
Defaults to 20

A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.
order

string
Optional
Defaults to desc

Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
after

string
Optional

A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
before

string
Optional

A cursor for use in pagination. before is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.
filter

string
Optional

Filter by file status. One of in_progress, completed, failed, cancelled.
Returns

A list of vector store file objects.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStoreFiles = await openai.beta.vectorStores.files.list(
    "vs_abc123"
  );
  console.log(vectorStoreFiles);
}

main();

Response

{
  "object": "list",
  "data": [
    {
      "id": "file-abc123",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    },
    {
      "id": "file-abc456",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    }
  ],
  "first_id": "file-abc123",
  "last_id": "file-abc456",
  "has_more": false
}

Retrieve vector store file
Beta
get https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}

Retrieves a vector store file.
Path parameters
vector_store_id

string
Required

The ID of the vector store that the file belongs to.
file_id

string
Required

The ID of the file being retrieved.
Returns

The vector store file object.
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const vectorStoreFile = await openai.beta.vectorStores.files.retrieve(
    "vs_abc123",
    "file-abc123"
  );
  console.log(vectorStoreFile);
}

main();

Response

{
  "id": "file-abc123",
  "object": "vector_store.file",
  "created_at": 1699061776,
  "vector_store_id": "vs_abcd",
  "status": "completed",
  "last_error": null
}

Delete vector store file
Beta
delete https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}

Delete a vector store file. This will remove the file from the vector store but the file itself will not be deleted. To delete the file, use the delete file endpoint.
Path parameters
vector_store_id

string
Required

The ID of the vector store that the file belongs to.
file_id

string
Required

The ID of the file to delete.
Returns

Deletion status
Example request

import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const deletedVectorStoreFile = await openai.beta.vectorStores.files.del(
    "vs_abc123",
    "file-abc123"
  );
  console.log(deletedVectorStoreFile);
}

main();

Response

{
  id: "file-abc123",
  object: "vector_store.file.deleted",
  deleted: true
}

The vector store file object
Beta

A list of files attached to a vector store.
id

string

The identifier, which can be referenced in API endpoints.
object

string

The object type, which is always vector_store.file.
usage_bytes

integer

The total vector store usage in bytes. Note that this may be different from the original file size.
created_at

integer

The Unix timestamp (in seconds) for when the vector store file was created.
vector_store_id

string

The ID of the vector store that the File is attached to.
status

string

The status of the vector store file, which can be either in_progress, completed, cancelled, or failed. The status completed indicates that the vector store file is ready for use.
last_error

object or null

The last error associated with this vector store file. Will be null if there are no errors.
chunking_strategy

object

The strategy used to chunk the file.