
# <center>DevRAG</center>

## Inspiration

Participating in this hackathon was an incredible opportunity to dive into the world of cutting-edge AI technologies. As our first hackathon experience, we were motivated to challenge ourselves and explore the potential of Retrieval-Augmented Generation (RAG) systems.The event provided us with a unique setlist for learning AI, allowing us to combine powerful tools like Cortex Search for retrieval, Mistral LLM (mistral-large2) on Snowflake Cortex for generation, and Streamlit Community Cloud for the front end.


Our vision was to build an innovative RAG application that simplifies how users interact with diverse information sources, such as GitHub repositories, PDFs, and web pages. By integrating these technologies, we aimed to create a personalized, efficient, and user-friendly query system that makes information retrieval more accessible and actionable.

This hackathon provided a platform to connect with the AI space and showcase our creativity in solving real-world challenges.Inspired by this collaborative environment, we discovered our capabilities, explored new tech stacks, and delivered a solution we’re truly proud of.



## What It Does  

### 🌟 Chatbot with Mistral AI LLM  
At the core of our application is a powerful chatbot built using Mistral LLM (mistral-large2) on Snowflake Cortex.
Users can ask queries, and the chatbot provides precise, context-aware responses.By leveraging advanced Retrieval-Augmented Generation (RAG) techniques, it ensures that users get highly relevant and actionable information.

### 🔍 GitHub Repository Scraper  
Users can input a GitHub repository URL, and the system scrapes its contents, including code files, README files, and documentation.The chatbot processes this data, allowing users to ask specific queries about the repository.This feature is particularly useful for developers working with large, open-source projects or exploring unfamiliar codebases.It simplifies understanding complex repositories by providing instant insights and answering targeted questions about functionality, structure, and usage.

### 📄 PDF Content Processing  
Our application supports PDF uploads, enabling users to analyze complex documents in seconds.The system extracts content from the attached PDFs and processes it for querying.Users can ask targeted questions about the document, such as summaries, details, or specific insights, simplifying research and document review.This feature is ideal for developers exploring lengthy tool documentation, research papers, or technical guides.

### 🌐 Website Content Scraper  
With a simple paste of a website URL, users can unlock the power of web content scraping.The application extracts and analyzes the information from the webpage and answers user queries with precision.Whether for research, competitive analysis, or general exploration, this feature makes information retrieval fast and easy.

### 🛠️ Unified Query System  with Streamlit Frontend
Bringing all these features together, the application offers a seamless and unified query system.Users can interact with GitHub repositories, PDFs, and websites in one place, ensuring a consistent and intuitive experience.
The Streamlit Community Cloud frontend provides a user-friendly interface for users to input queries and view results




## 🌟 Why Our Model Stands Out

Our project began with a vision to create a Retrieval-Augmented Generation (RAG) system tailored for developers working on new projects.When faced with learning a new tool or technology, developers can simply provide the tool’s documentation URL to our chatbot and ask specific queries.This eliminates the need to manually sift through lengthy documents, allowing for focused and efficient learning.

We further extended this idea by adding support for PDFs, enabling users to interact with technical guides, research papers, or product manuals in a personalized manner.

One of the standout features is the **GitHub Repository Scraping and Generation system**. Developers working on large open-source projects or trying to understand complex repositories can simply input the repo URL.The application then scrapes all relevant data and allows users to ask precise questions about functionality, architecture, or usage.This feature transforms the way developers interact with unfamiliar codebases, making onboarding and exploration faster and more intuitive.



## 🤖 How We Built It


### 🛠️ Technologies Used  
To build this RAG application, we leveraged the following tools and frameworks to ensure efficiency, scalability, and personalization:  
- **Cortex Search** for efficient retrieval of data from various sources.  
- **Mistral LLM (mistral-large2)** on Snowflake Cortex for natural language generation.  
- **Snowflake Arctic Embed Large - V2 Model** to enhance the generation capabilities and improve response quality.  
- **Streamlit Community Cloud** for building an interactive and user-friendly front end.  

### 🚀 Step-by-Step Development  

#### 1. **Building the Core RAG for Web Scraping**  
We began by designing a core RAG system to help developers quickly learn new tools.  
- Users could paste a **documentation URL** of a tool or library.  
- The system scraped the content of the URL and processed it for retrieval using Cortex Search.  
- Mistral LLM was then used to generate responses to user queries based on the extracted content.  

This initial system aimed to simplify the process of learning new tools by providing instant, query-based assistance.  

#### 2. **Extending to a Personalized RAG**  
To make the application more robust and user-focused, we expanded the core idea into a **personalized RAG system**:  
- Added **user authentication and login functionality** to allow personalized sessions.  
- Queries, attached URLs, and documents were stored in memory for each user, enabling context-aware responses.  
- Users could revisit their queries or continue from where they left off, creating a tailored experience.  

#### 3. **Adding GitHub Repository Integration**  
To enhance its usefulness for developers, we introduced a **GitHub repository scraping feature**:  
- Users could input a GitHub repository URL.  
- The system scraped repository contents, such as code files, README files, and documentation.  
- Queries specific to the repository, like understanding code structure or functionality, were supported, helping developers explore large or unfamiliar repositories with ease.  

#### 4. **Implementing PDF Parsing**  
We then added support for **PDF parsing** to handle technical guides, research papers, or lengthy documentation:  
- Users could upload PDFs directly to the system.  
- The content was extracted and indexed using Cortex Search.  
- The chatbot provided summaries, answered detailed questions, and delivered insights based on the document.  

#### 5. **Building a Unified Query System**  
To bring all features together, we built a **unified interactive query system**:  
- Integrated the ability to handle multiple data sources, including URLs, GitHub repositories, and PDFs, in one system.  
- Designed the interface to provide a seamless experience, where users could interact with any source of information without switching contexts.  

#### 6. **Developing the Frontend and Backend**  
The application was built with a strong focus on usability and performance:  
- The **frontend** was developed using **Streamlit Community Cloud**, ensuring an intuitive and interactive experience for users.  
- The **backend** integrated Cortex Search, Mistral LLM, and Snowflake Arctic Embed Large - V2 Model to provide a scalable and efficient infrastructure.  

#### 7. **Integration and Finalization**  
Finally, we focused on integrating all components to deliver a cohesive application:  
- Integration of the front end and back end.  
- Optimized the system for performance and accuracy.  
- Tested all features extensively to ensure reliability across different use cases.  



## Tech Stack used 

![Tech Stack](C:/Users/gcboo/OneDrive/Pictures/Screenshots/Screenshot 2025-01-21 235453.png)


## Challenges we ran into

### 1. 🔄 Personalization with Memory  
Implementing a personalized experience, where user queries, URLs, and uploaded documents were stored in memory, added an extra layer of complexity. Balancing memory management with performance optimization was crucial to ensure a responsive and scalable system.  

### 2. ⚡ Performance Optimization  
Ensuring low-latency responses while integrating advanced models like Mistral LLM and Snowflake Arctic Embed was critical. We had to optimize query processing and retrieval pipelines to deliver accurate and fast responses, even with large datasets.  

### 1. 🌐 Web Scraping Optimization  
Initially, we explored multiple web crawlers to minimize the time required to scrape websites efficiently. However, many tools either lacked flexibility or were too resource-intensive for our use case. After extensive research and testing, we decided to use **BeautifulSoup** in combination with **Crawl4AI**. This setup provided the perfect balance of speed and accuracy for parsing website content while handling diverse webpage structures.  

### 2. 🔄 Session Management in Streamlit  
Managing sessions in **Streamlit** was another challenge. To address this, we introduced object-oriented programming (OOP) concepts, which allowed us to build a custom session management layer. This enabled seamless session maintenance, providing users with a consistent and personalized experience throughout their interactions.  

### 3. ✨ Quality of Code Maintenance  
As the project grew in complexity, maintaining clean and readable code became critical. We focused on adhering to best practices for modularization, code readability, and reusability.This commitment to quality not only made the codebase easier to manage but also improved debugging and future scalability.  


## Accomplishments that we're proud of

### 🌟 Building Our First Personalized RAG System  
We’re proud to have successfully designed and implemented a **personalized Retrieval-Augmented Generation (RAG) system** in our first hackathon. Starting with a simple web scraping tool for documentation, we extended it into a comprehensive system capable of handling multiple data sources like URLs, GitHub repositories, and PDFs.  

### 🔗 Integrating Advanced Technologies  
Our team effectively integrated tools like **Cortex Search**, **Mistral LLM**, **Snowflake Arctic Embed V2**, and **Streamlit Community Cloud** into a unified application. This seamless integration allowed us to deliver a robust, high-performance system with diverse functionalities.  

### 🔍 Delivering a Unified Query System  
We’re proud of creating a unified interface where users can interact seamlessly with diverse data sources.

### 👩‍💻 Teamwork and Learning  
This project showcased the strength of our collaboration and adaptability. Being our first hackathon, we divided tasks effectively, shared knowledge, and worked together to achieve a common goal. We learned new technologies, refined our coding practices, and pushed ourselves beyond our comfort zones.  


### 🖥️ Full-Stack Deployment  
We successfully deployed a **full-stack application** with a customized and interactive interface built using **Streamlit**. The intuitive front end ensures a seamless user experience, making complex functionalities accessible and easy to use.  

### 🛠️ User-Personalized Architecture  
Our system features a **user-personalized architecture** that retains session-specific data, including queries, attached URLs, and documents. This ensures that users receive a tailored and consistent experience during interactions, significantly enhancing usability.  

### ✨ Tailored Responses  
The chatbot delivers **tailored responses** by leveraging the contextual understanding of user queries and the provided data sources. Whether interacting with a GitHub repository, PDF, or website URL, the responses are precise, relevant, and personalized to the user’s specific needs.  

## What we learned


### 🌟 Exploring New Technologies  
We gained hands-on experience with **Cortex Search**, **Mistral LLM**, **Snowflake Arctic Embed V2**, and **Streamlit Community Cloud**, understanding their capabilities and how to integrate them effectively.  

### 🛠️ Building a Personalized RAG System  
We learned how to design and implement a **personalized Retrieval-Augmented Generation system**, handling diverse data sources like URLs, GitHub repositories, and PDFs while maintaining session-specific data for tailored responses.  

### 🤝 Collaboration and Problem-Solving  
This project taught us the importance of effective teamwork, tackling technical challenges, and time management under tight deadlines, especially during a hackathon setting.  

## What's next for DevRAG

### 🎓 Create a Learning Platform  
We aim to transform **DevRAG** into a comprehensive learning platform for developers. This platform will provide:  
- **Saved sessions and progress tracking**, allowing users to revisit past queries and build on their knowledge.  

### 🌐 Expand Data Source Support  
We plan to enhance the system by integrating additional data sources, such as APIs, video transcripts, and cloud storage, to make it even more versatile.  

### 🤖 Advanced AI Features  
Incorporating **AI-powered recommendations** for queries and resources to guide users through learning paths tailored to their needs.  


