# import chromadb

# # aws chromaDB test code

# # 테스트 코드 클라이언트 인스턴스 생성 서버와 원활한 통신을 활성화하여 데이터 브릿지 역활
# chroma_client = chromadb.HttpClient(host='13.125.242.46', port=8005)


#     # Create a collection with a special touch (embedding function)
# collection = chroma_client.create_collection(name="test")
#     # Take a look at what's in the collection (don't forget the embedding function)
# collection = chroma_client.get_collection(name="test")

#     # Say goodbye to the collection
# chroma_client.delete_collection(name="my_collection")


# collection.add(
#     documents=["doc1", "doc2", "doc3"],
#     metadatas=[{"chapter": "3", "verse": "16"}, {"chapter": "3", "verse": "5"}],
#     ids=["id1", "id2", "id3"]
# )
