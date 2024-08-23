const express = require('express');
const { Storage } = require('@google-cloud/storage');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 8080;

require('dotenv').config();

const storage = new Storage({
    projectId: process.env.GCLOUD_PROJECT_ID,
    keyFilename: path.join(__dirname, process.env.GCLOUD_KEYFILE)
});

const bucketName = process.env.GCLOUD_BUCKET_NAME;

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

// Function to generate a signed URL
async function generateSignedUrl(fileName) {
    const options = {
        version: 'v4',
        action: 'read',
        expires: Date.now() + 15 * 60 * 1000, // 15 minutes
    };
    try {
        const [url] = await storage.bucket(bucketName).file(fileName).getSignedUrl(options);
        return url;
    } catch (error) {
        console.error(`Error generating signed URL for ${fileName}:`, error.message);
        return '/images/placeholder.png';
    }
}

app.get('/', async (req, res) => {
    try {
        const [files] = await storage.bucket(bucketName).getFiles({
            prefix: 'recipes/'
        });
        const recipes = await Promise.all(
            files
                .filter(file => file.name.endsWith('.json'))
                .map(async file => {
                    const [jsonContent] = await file.download();
                    const recipe = JSON.parse(jsonContent);
                    const imageUrl = await generateSignedUrl(file.name.replace('.json', '.png'));
                    return { ...recipe, id: file.name.split('/').pop().replace('.json', ''), imageUrl };
                })
        );
        res.render('index', { recipes });
    } catch (error) {
        console.error('Error fetching recipes:', error);
        res.status(500).send('Error fetching recipes');
    }
});

app.get('/recipe/:id', async (req, res) => {
        const recipeId = req.params.id;
        try {
            const file = storage.bucket(bucketName).file(`recipes/${recipeId}.json`);
            const [jsonContent] = await file.download();
            const recipe = JSON.parse(jsonContent);
            const imageUrl = await generateSignedUrl(`recipes/${recipeId}.png`);
            res.render('recipe', { recipe: { ...recipe, imageUrl } });
        } catch (error) {
            console.error('Error fetching recipe details:', error);
            res.status(500).send('Error fetching recipe details');
        }
    });

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
