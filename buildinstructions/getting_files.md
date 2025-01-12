Upload file
post https://api.openai.com/v1/files

Upload a file that can be used across various endpoints. Individual files can be up to 512 MB, and the size of all files uploaded by one organization can be up to 100 GB.

The Assistants API supports files up to 2 million tokens and of specific file types. See the Assistants Tools guide for details.

The Fine-tuning API only supports .jsonl files. The input also has certain required formats for fine-tuning chat or completions models.

The Batch API only supports .jsonl files up to 200 MB in size. The input also has a specific required format.

Please contact us if you need to increase these storage limits.
Request body
file

file
Required

The File object (not file name) to be uploaded.
purpose

string
Required

The intended purpose of the uploaded file.

Use "assistants" for Assistants and Message files, "vision" for Assistants image file inputs, "batch" for Batch API, and "fine-tune" for Fine-tuning.
Returns

The uploaded File object.
Example request

import fs from "fs";
import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const file = await openai.files.create({
    file: fs.createReadStream("mydata.jsonl"),
    purpose: "fine-tune",
  });

  console.log(file);
}

main();

Response

{
  "id": "file-abc123",
  "object": "file",
  "bytes": 120000,
  "created_at": 1677610602,
  "filename": "mydata.jsonl",
  "purpose": "fine-tune",
}

List files
get https://api.openai.com/v1/files

Returns a list of files.
Query parameters
purpose

string
Optional

Only return files with the given purpose.
limit

integer
Optional
Defaults to 10000

A limit on the number of objects to be returned. Limit can range between 1 and 10,000, and the default is 10,000.
order

string
Optional
Defaults to desc

Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.
after

string
Optional

A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
Returns

A list of File objects.
Example request

import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const list = await openai.files.list();

  for await (const file of list) {
    console.log(file);
  }
}

main();

Response

{
  "data": [
    {
      "id": "file-abc123",
      "object": "file",
      "bytes": 175,
      "created_at": 1613677385,
      "filename": "salesOverview.pdf",
      "purpose": "assistants",
    },
    {
      "id": "file-abc123",
      "object": "file",
      "bytes": 140,
      "created_at": 1613779121,
      "filename": "puppy.jsonl",
      "purpose": "fine-tune",
    }
  ],
  "object": "list"
}

Retrieve file
get https://api.openai.com/v1/files/{file_id}

Returns information about a specific file.
Path parameters
file_id

string
Required

The ID of the file to use for this request.
Returns

The File object matching the specified ID.
Example request

import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const file = await openai.files.retrieve("file-abc123");

  console.log(file);
}

main();

Response

{
  "id": "file-abc123",
  "object": "file",
  "bytes": 120000,
  "created_at": 1677610602,
  "filename": "mydata.jsonl",
  "purpose": "fine-tune",
}

Delete file
delete https://api.openai.com/v1/files/{file_id}

Delete a file.
Path parameters
file_id

string
Required

The ID of the file to use for this request.
Returns

Deletion status.
Example request

import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const file = await openai.files.del("file-abc123");

  console.log(file);
}

main();

Response

{
  "id": "file-abc123",
  "object": "file",
  "deleted": true
}

Retrieve file content
get https://api.openai.com/v1/files/{file_id}/content

Returns the contents of the specified file.
Path parameters
file_id

string
Required

The ID of the file to use for this request.
Returns

The file content.
Example request

import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const file = await openai.files.content("file-abc123");

  console.log(file);
}

main();

The file object

The File object represents a document that has been uploaded to OpenAI.
id

string

The file identifier, which can be referenced in the API endpoints.
bytes

integer

The size of the file, in bytes.
created_at

integer

The Unix timestamp (in seconds) for when the file was created.
filename

string

The name of the file.
object

string

The object type, which is always file.
purpose

string

The intended purpose of the file. Supported values are assistants, assistants_output, batch, batch_output, fine-tune, fine-tune-results and vision.
status
Deprecated

string

Deprecated. The current status of the file, which can be either uploaded, processed, or error.
status_details
Deprecated

string

Deprecated. For details on why a fine-tuning training file failed validation, see the error field on fine_tuning.job.
OBJECT The file object

{
  "id": "file-abc123",
  "object": "file",
  "bytes": 120000,
  "created_at": 1677610602,
  "filename": "salesOverview.pdf",
  "purpose": "assistants",
}