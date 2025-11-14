# GitHub API Research: Repository Scraping Patterns

**Research Date:** January 2025
**Purpose:** Comprehensive analysis of GitHub API for repository content scraping
**Status:** ✅ Complete

---

## Executive Summary

This research covers GitHub's REST API v3, GraphQL API, and best practices for repository scraping. Key findings include:

- **REST API** is better suited for file/directory access with simpler implementation
- **GraphQL API** offers efficient data fetching for complex queries but requires careful optimization
- **Authentication** is highly recommended (5,000 req/hr vs 60 req/hr unauthenticated)
- **Git Trees API** is optimal for retrieving full directory structures recursively

---

## 1. GitHub URL Pattern Detection

### 1.1 Common GitHub URL Formats

GitHub repositories can be accessed through multiple URL patterns:

```
# HTTPS URLs
https://github.com/{owner}/{repo}
https://github.com/{owner}/{repo}.git
https://github.com/{owner}/{repo}/tree/{branch}
https://github.com/{owner}/{repo}/tree/{branch}/{path}
https://github.com/{owner}/{repo}/blob/{branch}/{filepath}

# SSH URLs
git@github.com:{owner}/{repo}.git

# Raw Content URLs
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}

# API URLs
https://api.github.com/repos/{owner}/{repo}/contents/{path}
```

### 1.2 URL Parsing Strategy

**Recommended Regex Pattern:**
```regex
https?://github\.com/(?<owner>[^/]+)/(?<repo>[^/]+)(?:\.git)?(?:/(?<type>tree|blob)/(?<branch>[^/]+)(?:/(?<path>.+))?)?
```

**Extracted Components:**
- `owner`: Repository owner (user or organization)
- `repo`: Repository name (without .git extension)
- `type`: Content type (`tree` for directories, `blob` for files)
- `branch`: Branch/tag name (defaults to repository's default branch if omitted)
- `path`: File or directory path within the repository

**Parsing Libraries:**
- **JavaScript/TypeScript**: `parse-github-url` (npm package)
- **Python**: `giturlparse` (supports GitHub, GitLab, Bitbucket)

### 1.3 URL Type Classification

```typescript
enum GitHubUrlType {
  REPOSITORY = 'repository',      // https://github.com/owner/repo
  DIRECTORY = 'directory',         // .../tree/branch/path
  FILE = 'file',                   // .../blob/branch/filepath
  RAW = 'raw',                     // raw.githubusercontent.com
  API = 'api'                      // api.github.com
}
```

---

## 2. GitHub REST API v3

### 2.1 Repository Contents API

**Base Endpoint:** `GET /repos/{owner}/{repo}/contents/{path}`

**Required Parameters:**
- `owner` - Repository account owner (case-insensitive)
- `repo` - Repository name without .git extension
- `path` - File or directory path (optional for root)

**Optional Parameters:**
- `ref` - Branch name, tag, or commit SHA (defaults to repository's default branch)

**Example Request:**
```bash
curl -H "Accept: application/vnd.github+json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/contents/src/utils?ref=main
```

**Response Types:**
- **File**: Returns single object with base64-encoded content
- **Directory**: Returns array of objects for each item
- **Symlink**: Returns object with symlink target
- **Submodule**: Returns object with submodule information

### 2.2 File Size Limitations

| File Size | Behavior |
|-----------|----------|
| ≤ 1 MB | Full support, content field contains base64-encoded data |
| 1-100 MB | Only raw/object media types work, content field is empty |
| > 100 MB | Endpoint not supported, must use Git Data API |

**Directory Limit:** Maximum 1,000 files per directory. Use Git Trees API for larger directories.

### 2.3 Custom Media Types

```bash
# Raw file content (no base64 encoding)
Accept: application/vnd.github.raw+json

# HTML-rendered content (for markdown, etc.)
Accept: application/vnd.github.html+json

# Consistent object format
Accept: application/vnd.github.object+json
```

### 2.4 Git Trees API (Recommended for Scraping)

**Endpoint:** `GET /repos/{owner}/{repo}/git/trees/{tree_sha}`

**Key Parameter:** `recursive=1` - Retrieves entire directory tree recursively

**Advantages:**
- Single request for entire repository structure
- No 1,000-file directory limit
- Returns all files and directories with SHA, size, and type
- Up to 100,000 entries and 7 MB response size

**Example Request:**
```bash
curl -H "Accept: application/vnd.github+json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/git/trees/main?recursive=1
```

**Response Structure:**
```json
{
  "sha": "tree-sha",
  "url": "api-url",
  "tree": [
    {
      "path": "src/index.ts",
      "mode": "100644",
      "type": "blob",
      "sha": "file-sha",
      "size": 1234,
      "url": "blob-url"
    },
    {
      "path": "src/utils",
      "mode": "040000",
      "type": "tree",
      "sha": "dir-sha",
      "url": "tree-url"
    }
  ],
  "truncated": false
}
```

**File Modes:**
- `100644` - Regular file
- `100755` - Executable file
- `040000` - Subdirectory
- `120000` - Symlink
- `160000` - Git submodule

### 2.5 Getting Raw File Content

**Method 1: Using raw.githubusercontent.com**
```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}
```
- Direct binary content (no base64 encoding)
- Requires authentication for private repos
- Uses query parameter `?token=...` for auth

**Method 2: Using Contents API with raw media type**
```bash
curl -H "Accept: application/vnd.github.raw" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/contents/path/to/file?ref=branch
```

**Method 3: Using Git Blob API**
```bash
# First get blob SHA from tree, then fetch blob
curl -H "Accept: application/vnd.github+json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/git/blobs/{blob_sha}
```

---

## 3. Rate Limiting Strategies

### 3.1 Primary Rate Limits (REST API)

| Authentication | Requests per Hour | Use Case |
|----------------|-------------------|----------|
| Unauthenticated | 60 | Testing only, not recommended |
| Personal Access Token | 5,000 | Individual users |
| OAuth App | 5,000 | User-authorized apps |
| GitHub App | 5,000 (base) | Automated integrations |
| GitHub App (Enterprise) | 15,000 | Enterprise customers |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1372700873
X-RateLimit-Used: 1
X-RateLimit-Resource: core
```

### 3.2 Secondary Rate Limits

Additional restrictions beyond primary limits:

1. **Concurrent Requests:** Max 100 concurrent requests (shared across REST + GraphQL)
2. **REST Points:** Max 900 points/minute for REST endpoints
3. **CPU Time:** Max 90 seconds CPU time per 60 seconds real time
4. **Content Creation:** Max 80 requests/minute for creating content

### 3.3 GraphQL API Rate Limits

**Point-Based System:**
- **Standard users:** 5,000 points/hour
- **GitHub Apps (Enterprise):** 10,000 points/hour
- **Minimum query cost:** 1 point
- **Additional limits:** 2,000 points/minute

**Calculating Query Cost:**
1. Multiply pagination arguments across nested connections
2. Divide total requests by 100 and round to nearest whole number
3. Minimum cost is always 1 point

**Example:**
```
Query: 100 repositories × 50 issues × 60 labels = 300,000 requests
Cost: 300,000 ÷ 100 = 3,000 points
```

### 3.4 2025 Update: Timeout Penalties

**Important Change (July 2025):** Request timeouts now count against primary rate limits. If your integration experiences timeouts, you may hit hourly limits sooner than expected.

### 3.5 Rate Limit Best Practices

1. **Always Authenticate:** 5,000 vs 60 requests/hour makes authentication essential
2. **Use Conditional Requests:** ETags and Last-Modified headers reduce unnecessary data transfer
3. **Implement Exponential Backoff:** When rate limited, wait until `X-RateLimit-Reset` time
4. **Cache Aggressively:** Store responses and reuse when possible
5. **Batch Operations:** Use GraphQL or Git Trees API to reduce request count
6. **Monitor Usage:** Check `X-RateLimit-Remaining` header proactively
7. **Use GitHub Apps:** Better scalability for production applications

**Checking Rate Limit:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/rate_limit
```

---

## 4. Authentication Requirements

### 4.1 Authentication Methods (Ranked by Best Practice)

| Method | Security | Scalability | Use Case | Recommendation |
|--------|----------|-------------|----------|----------------|
| GitHub Apps | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Production automation | **Best** for apps |
| Fine-grained PATs | ⭐⭐⭐⭐ | ⭐⭐⭐ | Limited repository access | **Best** for scoped access |
| Classic PATs | ⭐⭐⭐ | ⭐⭐⭐ | Personal scripts | Good for simple tools |
| OAuth Apps | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | User-authorized applications | Legacy, use GitHub Apps |
| Unauthenticated | ⭐ | ⭐ | Public data testing | **Avoid** in production |

### 4.2 Personal Access Tokens (PATs)

**Best Practices:**
1. **Minimal Scopes:** Only request necessary permissions
   - `public_repo` - Access public repositories (read-only)
   - `repo` - Full control of private repositories (read/write)
2. **Environment Variables:** Never hardcode tokens
3. **Token Rotation:** Rotate every 6 months (70% fewer breaches)
4. **Expiration:** Set expiration dates on all tokens
5. **Monitoring:** Use audit logs to track token usage

**Required Scopes for Repository Scraping:**
- Public repositories: No authentication required (but recommended)
- Private repositories: `repo` scope minimum

**Example Usage:**
```bash
# Header-based authentication (recommended)
curl -H "Authorization: Bearer ghp_xxxxxxxxxxxx" \
     https://api.github.com/repos/owner/repo

# Query parameter (legacy, avoid)
curl https://api.github.com/repos/owner/repo?access_token=ghp_xxxx
```

### 4.3 GitHub Apps Advantages

**Fine-Grained Permissions:**
- Read access to specific files/directories
- Repository-level access control
- Automatic permission reviews

**Better Rate Limits:**
- Base: 5,000 requests/hour per installation
- Bonus: +50 requests/hour per repository (for installations with 20+ repos)

**Security Benefits:**
- Least privilege principle
- Installation-level access control
- Automatic token rotation

### 4.4 Authentication Recommendations

**For Scraping Public Repositories:**
- Minimum: Classic PAT with `public_repo` scope
- Recommended: Fine-grained PAT with read-only repository permissions
- Production: GitHub App with repository contents: read permission

**For Scraping Private Repositories:**
- Minimum: Classic PAT with `repo` scope
- Recommended: Fine-grained PAT with specific repository access
- Production: GitHub App with repository contents: read permission per installation

---

## 5. Implementation Recommendations

### 5.1 Recommended Approach for Repository Scraping

**Step 1: Parse GitHub URL**
```typescript
interface ParsedGitHubUrl {
  owner: string;
  repo: string;
  branch?: string;
  path?: string;
  type: 'repository' | 'directory' | 'file';
}

function parseGitHubUrl(url: string): ParsedGitHubUrl {
  const regex = /github\.com\/(?<owner>[^/]+)\/(?<repo>[^/]+)(?:\/(?<type>tree|blob)\/(?<branch>[^/]+)(?:\/(?<path>.+))?)?/;
  const match = url.match(regex);
  // Parse and return structured data
}
```

**Step 2: Get Default Branch (if not specified)**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo
# Response includes "default_branch" field
```

**Step 3: Retrieve Repository Tree**
```bash
# Get entire repository structure in one request
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/git/trees/main?recursive=1
```

**Step 4: Download Files**
```bash
# Option A: Use raw.githubusercontent.com (faster, less rate limit impact)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://raw.githubusercontent.com/owner/repo/branch/path/to/file

# Option B: Use Git Blob API (for integrity verification)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/owner/repo/git/blobs/{blob_sha}
```

### 5.2 Workflow Diagram

```
┌─────────────────┐
│  GitHub URL     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse URL      │ Extract owner, repo, branch, path
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Get Repo Info  │ Fetch default branch if needed
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Get Tree SHA   │ Get tree SHA for branch/commit
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Fetch Tree     │ GET /git/trees/{sha}?recursive=1
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Filter Files   │ Filter by path if specified
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Download Files │ Parallel downloads with rate limit control
└─────────────────┘
```

### 5.3 Error Handling

**Common API Errors:**

| Status Code | Meaning | Recommended Action |
|-------------|---------|-------------------|
| 401 | Unauthorized | Verify token validity and scopes |
| 403 | Forbidden / Rate Limited | Check `X-RateLimit-Remaining`, wait until reset |
| 404 | Not Found | Verify repository exists and is accessible |
| 409 | Git Repository Empty | Handle empty repositories gracefully |
| 422 | Validation Failed | Check request parameters |
| 500 | Server Error | Retry with exponential backoff |

**Rate Limit Handling:**
```typescript
async function handleRateLimit(response: Response): Promise<void> {
  const remaining = parseInt(response.headers.get('X-RateLimit-Remaining') || '0');
  const resetTime = parseInt(response.headers.get('X-RateLimit-Reset') || '0');

  if (remaining === 0) {
    const waitTime = (resetTime * 1000) - Date.now();
    console.log(`Rate limited. Waiting ${waitTime}ms until reset...`);
    await sleep(waitTime);
  }
}
```

### 5.4 Performance Optimization

**Parallel Downloads:**
```typescript
const MAX_CONCURRENT = 10; // Stay under secondary rate limits

async function downloadFilesInParallel(files: GitHubFile[], concurrency: number) {
  const chunks = chunkArray(files, concurrency);

  for (const chunk of chunks) {
    await Promise.all(
      chunk.map(file => downloadFile(file))
    );
  }
}
```

**Caching Strategy:**
```typescript
interface CacheEntry {
  etag: string;
  lastModified: string;
  data: any;
  timestamp: number;
}

// Use ETags for conditional requests
headers['If-None-Match'] = cachedEtag;
// 304 Not Modified response = use cached data
```

### 5.5 Branch and Tag Support

**Getting All Branches:**
```bash
GET /repos/{owner}/{repo}/branches
```

**Getting All Tags:**
```bash
GET /repos/{owner}/{repo}/tags
```

**Default Branch Detection:**
```bash
GET /repos/{owner}/{repo}
# Response contains "default_branch" field
```

**Commit SHA Resolution:**
```bash
# Get commit SHA for any ref (branch, tag, or commit)
GET /repos/{owner}/{repo}/commits/{ref}
```

---

## 6. Code Examples

### 6.1 Basic Repository Tree Fetching

```typescript
import { Octokit } from '@octokit/rest';

const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN
});

async function getRepositoryTree(owner: string, repo: string, branch: string = 'main') {
  try {
    // Get repository info to verify default branch
    const { data: repoData } = await octokit.repos.get({
      owner,
      repo
    });

    const branchToUse = branch || repoData.default_branch;

    // Get the tree SHA for the branch
    const { data: refData } = await octokit.git.getRef({
      owner,
      repo,
      ref: `heads/${branchToUse}`
    });

    const treeSha = refData.object.sha;

    // Get the full tree recursively
    const { data: treeData } = await octokit.git.getTree({
      owner,
      repo,
      tree_sha: treeSha,
      recursive: 'true'
    });

    return treeData.tree;
  } catch (error) {
    console.error('Error fetching repository tree:', error);
    throw error;
  }
}
```

### 6.2 Downloading File Content

```typescript
async function downloadFileContent(
  owner: string,
  repo: string,
  path: string,
  branch: string = 'main'
): Promise<string> {
  try {
    // Option 1: Using Contents API with raw media type
    const { data } = await octokit.repos.getContent({
      owner,
      repo,
      path,
      ref: branch,
      mediaType: {
        format: 'raw'
      }
    });

    return data as unknown as string;
  } catch (error) {
    console.error(`Error downloading file ${path}:`, error);
    throw error;
  }
}

// Alternative: Using fetch for raw.githubusercontent.com
async function downloadFileRaw(
  owner: string,
  repo: string,
  path: string,
  branch: string = 'main',
  token?: string
): Promise<string> {
  const url = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`;
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new Error(`Failed to download ${path}: ${response.statusText}`);
  }

  return response.text();
}
```

### 6.3 Rate Limit Monitoring

```typescript
async function checkRateLimit(octokit: Octokit): Promise<void> {
  const { data } = await octokit.rateLimit.get();

  const { core, graphql } = data.resources;

  console.log('REST API Rate Limit:');
  console.log(`  Limit: ${core.limit}`);
  console.log(`  Remaining: ${core.remaining}`);
  console.log(`  Reset: ${new Date(core.reset * 1000).toISOString()}`);

  console.log('\nGraphQL API Rate Limit:');
  console.log(`  Limit: ${graphql.limit}`);
  console.log(`  Remaining: ${graphql.remaining}`);
  console.log(`  Reset: ${new Date(graphql.reset * 1000).toISOString()}`);

  if (core.remaining < 100) {
    console.warn('\n⚠️  Warning: Low rate limit remaining!');
  }
}
```

### 6.4 URL Parsing

```typescript
interface ParsedGitHubUrl {
  owner: string;
  repo: string;
  branch?: string;
  path?: string;
  type: 'repository' | 'directory' | 'file';
  isValid: boolean;
}

function parseGitHubUrl(url: string): ParsedGitHubUrl {
  const regex = /^https?:\/\/github\.com\/(?<owner>[^/]+)\/(?<repo>[^/]+?)(?:\.git)?(?:\/(?<contentType>tree|blob)\/(?<branch>[^/]+)(?:\/(?<path>.+))?)?$/;

  const match = url.match(regex);

  if (!match || !match.groups) {
    return {
      owner: '',
      repo: '',
      type: 'repository',
      isValid: false
    };
  }

  const { owner, repo, contentType, branch, path } = match.groups;

  let type: 'repository' | 'directory' | 'file' = 'repository';
  if (contentType === 'tree') {
    type = 'directory';
  } else if (contentType === 'blob') {
    type = 'file';
  }

  return {
    owner,
    repo: repo.replace(/\.git$/, ''),
    branch,
    path,
    type,
    isValid: true
  };
}

// Example usage
const parsed = parseGitHubUrl('https://github.com/owner/repo/tree/main/src/utils');
// {
//   owner: 'owner',
//   repo: 'repo',
//   branch: 'main',
//   path: 'src/utils',
//   type: 'directory',
//   isValid: true
// }
```

---

## 7. GraphQL API Considerations

### 7.1 When to Use GraphQL

**Advantages:**
- Fetch multiple related resources in a single request
- Reduce over-fetching by selecting only needed fields
- Better for complex queries with nested relationships

**Disadvantages:**
- More complex query construction
- Point-based rate limiting requires cost calculation
- Steeper learning curve

### 7.2 GraphQL Query Example

```graphql
query GetRepositoryFiles($owner: String!, $repo: String!, $expression: String!) {
  repository(owner: $owner, name: $repo) {
    object(expression: $expression) {
      ... on Tree {
        entries {
          name
          type
          mode
          object {
            ... on Blob {
              byteSize
              text
            }
            ... on Tree {
              entries {
                name
                type
              }
            }
          }
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "owner": "octocat",
  "repo": "Hello-World",
  "expression": "main:src"
}
```

### 7.3 GraphQL Rate Limit Best Practices

1. **Use fragments** to avoid repeating field selections
2. **Limit pagination** to reasonable values (10-50 items per page)
3. **Avoid deep nesting** beyond 3-4 levels
4. **Calculate cost** before executing expensive queries
5. **Use persisted queries** for frequently-used queries

---

## 8. Security Considerations

### 8.1 Token Storage

**Never commit tokens to version control:**
```bash
# .env file (add to .gitignore)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**Use environment-specific configurations:**
```typescript
const token = process.env.GITHUB_TOKEN;
if (!token) {
  throw new Error('GITHUB_TOKEN environment variable is required');
}
```

### 8.2 Scope Minimization

**Principle of Least Privilege:**
- Public repos: `public_repo` scope only
- Private repos: Fine-grained PAT with specific repository access
- Production: GitHub App with minimal permissions

### 8.3 Audit Logging

**Monitor token usage:**
- GitHub provides audit logs for token activity
- Set up alerts for unusual access patterns
- Regularly review token usage in Settings → Developer settings

### 8.4 Token Rotation Policy

**Recommended Schedule:**
- Development tokens: 3-6 months
- Production tokens: Monthly rotation
- Compromised tokens: Immediate revocation and rotation

---

## 9. Testing Strategies

### 9.1 Public Repository Testing

**Test with public repositories first:**
```bash
# Test rate limits with unauthenticated requests
curl https://api.github.com/repos/octocat/Hello-World

# Test with authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/octocat/Hello-World
```

### 9.2 Mock API Responses

**Use tools like nock for testing:**
```typescript
import nock from 'nock';

nock('https://api.github.com')
  .get('/repos/owner/repo/git/trees/main')
  .query({ recursive: '1' })
  .reply(200, {
    sha: 'tree-sha',
    tree: [
      { path: 'README.md', type: 'blob', sha: 'blob-sha', size: 1234 }
    ]
  });
```

### 9.3 Rate Limit Testing

**Simulate rate limit scenarios:**
```typescript
// Test rate limit handling
nock('https://api.github.com')
  .get('/repos/owner/repo')
  .reply(403, 'Rate limit exceeded', {
    'X-RateLimit-Remaining': '0',
    'X-RateLimit-Reset': String(Math.floor(Date.now() / 1000) + 3600)
  });
```

---

## 10. Summary & Quick Reference

### 10.1 API Comparison Matrix

| Feature | REST API | GraphQL API | Git Trees API |
|---------|----------|-------------|---------------|
| **Learning Curve** | Easy | Medium | Easy |
| **Single Request Tree** | ❌ No | ✅ Yes | ✅ Yes |
| **File Size Limit** | 100 MB | N/A | No limit |
| **Rate Limit Type** | Request-based | Point-based | Request-based |
| **Best For** | Simple file access | Complex queries | Full repo scraping |
| **Directory Limit** | 1,000 files | No limit | 100,000 entries |

### 10.2 Recommended Technology Stack

```json
{
  "authentication": "Personal Access Token (PAT) or GitHub App",
  "library": "@octokit/rest (JavaScript/TypeScript)",
  "primary-api": "Git Trees API with recursive=1",
  "file-download": "raw.githubusercontent.com for efficiency",
  "rate-limit-strategy": "Header-based monitoring with exponential backoff",
  "caching": "ETag-based conditional requests",
  "parallelization": "Max 10 concurrent requests"
}
```

### 10.3 Critical Endpoints

```bash
# Get repository information (default branch)
GET /repos/{owner}/{repo}

# Get full repository tree (RECOMMENDED)
GET /repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1

# Get file contents (base64-encoded)
GET /repos/{owner}/{repo}/contents/{path}?ref={branch}

# Get raw file content
Accept: application/vnd.github.raw
GET /repos/{owner}/{repo}/contents/{path}

# Alternative raw content
GET https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}

# Check rate limits
GET /rate_limit
```

### 10.4 Essential Rate Limit Facts

- **Authenticated:** 5,000 requests/hour
- **Unauthenticated:** 60 requests/hour
- **Secondary limit:** 100 concurrent requests
- **Timeout penalty:** Timeouts count against rate limit (2025 update)
- **Reset time:** Check `X-RateLimit-Reset` header

### 10.5 Implementation Checklist

- [ ] Parse GitHub URL (owner, repo, branch, path)
- [ ] Set up authentication (PAT or GitHub App)
- [ ] Get repository default branch if not specified
- [ ] Fetch repository tree using Git Trees API (recursive=1)
- [ ] Filter tree entries by path if needed
- [ ] Download files using raw.githubusercontent.com or Blob API
- [ ] Implement rate limit monitoring and backoff
- [ ] Add error handling for 401, 403, 404, 422, 500 responses
- [ ] Cache responses using ETags
- [ ] Support multiple branches and tags
- [ ] Handle large repositories (>100,000 files)
- [ ] Implement parallel downloads with concurrency control
- [ ] Store tokens securely in environment variables
- [ ] Set up token rotation policy
- [ ] Add comprehensive logging and monitoring

---

## 11. Additional Resources

### 11.1 Official Documentation

- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [GitHub GraphQL API Documentation](https://docs.github.com/en/graphql)
- [Repository Contents API](https://docs.github.com/en/rest/repos/contents)
- [Git Trees API](https://docs.github.com/en/rest/git/trees)
- [Rate Limits Documentation](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Authentication Guide](https://docs.github.com/en/rest/authentication)

### 11.2 Recommended Libraries

**JavaScript/TypeScript:**
- `@octokit/rest` - Official GitHub REST API client
- `@octokit/graphql` - Official GitHub GraphQL client
- `parse-github-url` - URL parsing utility

**Python:**
- `PyGithub` - Python library for GitHub API
- `giturlparse` - Git URL parsing library

### 11.3 Tools

- [GitHub CLI](https://cli.github.com/) - Official command-line interface
- [GitHub API Explorer](https://docs.github.com/en/graphql/overview/explorer) - GraphQL query testing
- [Postman GitHub Collections](https://www.postman.com/github) - API testing collections

---

## Appendix: Research Sources

1. GitHub REST API Documentation - Official GitHub Docs
2. GitHub GraphQL API Rate Limits - Official GitHub Docs
3. GitHub Authentication Best Practices - Official GitHub Docs
4. Stack Overflow - GitHub URL parsing patterns and solutions
5. npm packages: `parse-github-url`, `@octokit/rest`
6. Python libraries: `giturlparse`, `PyGithub`
7. GitHub Changelog - 2025 Rate Limit Updates

---

**Document Version:** 1.0
**Last Updated:** January 2025
**Researcher:** Hive Mind Swarm - Research Agent
**Session ID:** swarm-1763159183466-ozce54lgp
