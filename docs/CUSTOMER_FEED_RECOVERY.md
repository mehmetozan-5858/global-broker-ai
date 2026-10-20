# Customer feed loading and recovery

Customer loading errors are distinct from a successful empty opportunity list. Missing/expired sessions prompt account login with an allowlisted `/customer` return destination. HTTP 403 directs users to account access settings without claiming a purchase is required. HTTP 429 asks the user to wait. Network/server failures, invalid JSON, and malformed feed shapes display a retry message rather than a false empty result. Raw server diagnostics are never rendered.

Access and introduction-history reads run concurrently; history is non-blocking. Each JSON read has a 15-second abort deadline. A failed read removes old cards. Manual retries are single-flight, clear request state, reload account access and data, and add no payment/introduction writes. Portal styles are installed once. A valid empty response retains normal filter/sector-selection guidance; all-sector accounts do not receive a misleading sector-selection prompt.

Validation: the unit harness covers 401/403/429/503, missing session, network failure, malformed response, non-JSON errors, abort cleanup and rapid retry clicks. The existing deployed-script browser check now exercises the same states, recovery to real-shaped fixtures, login return, true empty results and privacy on Chromium 320/390/1280 and WebKit 390. Browser service requests are intercepted; no real user records or transactions are created.

This is software behavior verification, not real customer acceptance or provider approval. Weighted delivery percentages are unchanged.
