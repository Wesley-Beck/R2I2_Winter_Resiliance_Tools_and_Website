# Google Cloud Setup Guide

This guide walks through setting up the Google services needed for the R2I2 website.

## 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **New Project** and name it (e.g., "R2I2 Winter Resilience")
3. Note the Project ID

## 2. Enable APIs

In your project, go to **APIs & Services > Library** and enable:
- **Google Identity Services** (for Sign-In)

## 3. OAuth 2.0 Client ID

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Web application**
4. Name: "R2I2 Website"
5. Authorized JavaScript origins:
   - `http://localhost:5173` (for local development)
   - `https://wesley-beck.github.io` (for production)
6. Click **Create** and copy the **Client ID**
7. Update `src/config.js` with your Client ID:
   ```js
   clientId: 'your-client-id.apps.googleusercontent.com',
   ```

## 4. CMS Google Sheet

Create a Google Sheet with the following tabs. The website fetches data from this sheet at runtime.

### Sheet Tabs

#### TeamMembers
| visible | name | role | org | interests | link | category |
|---------|------|------|-----|-----------|------|----------|
| TRUE | Ana Dyreson | Principal Investigator | Michigan Tech | Climate-informed... | https://... | core |

**category** values: `core`, `planning`

#### News
| visible | title | date | summary | tag |
|---------|-------|------|---------|-----|
| TRUE | NSF Awards R2I2 Grant... | August 2025 | Michigan Tech leads... | Award |

#### Workshops
| visible | id | title | description | status | date | formUrl |
|---------|----|----|-------------|--------|------|---------|
| TRUE | 1 | Future Winter Weather... | Exploring current... | upcoming | TBD - Fall 2026 | |

#### Tools
| visible | name | link | description |
|---------|------|------|-------------|
| TRUE | ClimRR Local Projections | https://climrr.anl.gov/... | Climate risk... |

#### DataPortals
| visible | name | link |
|---------|------|------|
| TRUE | NASA Earthdata | https://earthdata.nasa.gov/ |

#### PortalFiles
| visible | group | folder | title | googleFileId | fileType |
|---------|-------|--------|-------|--------------|----------|
| TRUE | core | Meeting Notes | Planning Meeting 1 | 1abc...xyz | doc |
| TRUE | all | Resources | Project Overview | 2def...abc | slide |

**group** values: `core`, `planning`, `all` (all = visible to everyone)
**fileType** values: `doc`, `sheet`, `slide`, `form`, `pdf`, `file`

#### PortalPermissions
| email | group |
|-------|-------|
| researcher@mtu.edu | core |
| committee@anl.gov | planning |

### Publish the Sheet

1. Open the Google Sheet
2. Go to **File > Share > Publish to web**
3. Select **Entire Document** and **Web page**
4. Click **Publish**
5. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
6. Update `src/config.js`:
   ```js
   sheetId: 'your-sheet-id',
   ```

## 5. Google Calendar

1. Create a Google Calendar for the project (or use an existing one)
2. Go to **Settings > Settings for my calendars > [Your Calendar]**
3. Under **Integrate calendar**, copy the **Calendar ID**
4. Make the calendar **public** (Settings > Access permissions > Make available to public)
5. Update `src/config.js`:
   ```js
   calendarId: 'your-calendar-id@group.calendar.google.com',
   ```

## 6. Summary of Config Values

After setup, your `src/config.js` should look like:

```js
export const GOOGLE_CONFIG = {
  clientId: 'xxxx.apps.googleusercontent.com',
  sheetId: 'xxxx',
  calendarId: 'xxxx@group.calendar.google.com',
  driveFolderId: '1gQfKJ4kRUrdmce61cx9K3ghnC9_EPQl8',
};
```

## 7. How Content Updates Work

- **Team members, news, workshops, tools, data portals**: Edit the corresponding tab in the Google Sheet. Set the `visible` column to `TRUE` or `FALSE` to show/hide items. Changes appear on the website when visitors reload the page.
- **Portal files**: Add a row to the `PortalFiles` tab with the Google file ID, file type, target group, and folder name. The file will appear in that group's portal section.
- **Portal permissions**: Add a user's email and group to the `PortalPermissions` tab. They will see that group's files after signing in.
