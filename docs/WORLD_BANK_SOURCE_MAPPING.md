# World Bank procurement source mapping

The live `search.worldbank.org/api/v2/procnotices` response uses
`project_ctry_name`, `submission_deadline_date`, `contact_organization`,
`noticedate` and `procurement_method_name`. Previously the requested fields used
names from a different published procurement dataset. This returned bid titles
without the country, deadline or buyer organization required by the dossier.

Request the current API's explicit non-contact field list. Procurement organization
is retained privately; personal names, email, phone, address and raw notice HTML
are not requested. The organization field is a source fact, not completed buyer
due diligence. Project names never substitute for an actual buyer institution.

Strict OP-plus-eight-digit identifiers map to the official canonical
`https://projects.worldbank.org/en/projects-operations/procurement-detail/OP...`
address. `world_bank_source_fields` marks this as a canonical notice ID mapping.
Constructing the address does not establish HTTP reachability, document access,
full specification extraction, or any commercial approval. The existing reader
must still fetch and assess source documents.

Regional project labels such as Western and Central Africa remain recorded as a
project region and cannot fill the country requirement. Missing quantities,
budgets, exact specifications or supplier prices remain missing. No estimate is
created from a project title, location, financing amount or notice identifier.

Tests cover the actual response shape, the requested field contract, buyer versus
project identity, regional country ambiguity, strict source identifiers and public
masking after the recovered country/date enter the dossier. Provider-source
failures retain the existing zero-row behavior. The full scan must verify the
changed source stream before any delivery package is closed.

Primary source references:
- https://search.worldbank.org/api/v2/procnotices
- https://financesone.worldbank.org/procurement-notice/DS00979 (documents the
  canonical OP notice address; its column names differ from the search API).
